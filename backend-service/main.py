import os
import logging
import uvicorn
from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, Field # Use Pydantic for request/response validation
import google.generativeai as genai
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware


# --- Configuration ---
load_dotenv()  # Load environment variables from .env file

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Google Gemini API Configuration ---
API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL_NAME = "gemini-2.0-flash" # Or choose another compatible model
SYSTEM_PROMPT = """
You are a helpful and concise AI assistant specialized in providing professional responses.
Directly address the user's query without unnecessary pleasantries or small talk.
Maintain a formal and informative tone.
"""

# --- Initialize FastAPI App ---
app = FastAPI(
    title="Gemini Prompt Service",
    description="A FastAPI service to interact with Google Gemini API using system and user prompts.",
    version="1.0.0",
)

# --- CORS Middleware ---
# List of origins that are allowed to make requests.
# Use "*" for development only (allows all origins), but be more specific in production.
origins = [
    "http://localhost:3000", # Your React frontend development server
    "http://127.0.0.1:3000",
    # Add any other origins if needed (e.g., your production frontend URL)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True, # Allows cookies if needed
    allow_methods=["*"],    # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],    # Allows all headers
)

# --- Global Variables ---
gemini_model = None

# --- Pydantic Models ---
class PromptInput(BaseModel):
    user_prompt: str = Field(..., min_length=1, description="The prompt provided by the user.")

class GeminiResponse(BaseModel):
    response: str = Field(..., description="The generated text response from the Gemini model.")

class HealthStatus(BaseModel):
    status: str = Field("ok", description="Health status indicator")

class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Description of the error.")


# --- Application Startup Event ---
@app.on_event("startup")
async def startup_event():
    """
    Initialize Gemini client on application startup.
    """
    global gemini_model
    if not API_KEY:
        logger.error("FATAL: GOOGLE_API_KEY not found in environment variables. Service cannot start properly.")
        # In a real scenario, you might want the app to fail startup here,
        # but for simplicity, we'll let it run and endpoints will return errors.
        return # Exit startup event

    try:
        genai.configure(api_key=API_KEY)
        gemini_model = genai.GenerativeModel(MODEL_NAME)
        # Perform a simple test call to ensure connectivity (optional but recommended)
        # await gemini_model.generate_content_async("test") # Use async if needed elsewhere
        gemini_model.generate_content("test") # Simple sync test
        logger.info(f"Google Generative AI configured successfully with model: {MODEL_NAME}")
    except Exception as e:
        logger.error(f"Error initializing Google Generative AI or model '{MODEL_NAME}': {e}", exc_info=True)
        gemini_model = None # Ensure model is None if initialization fails

# --- API Endpoints ---

@app.get(
    "/health",
    tags=["Health"],
    summary="Perform a Health Check",
    response_model=HealthStatus,
    status_code=status.HTTP_200_OK,
)
async def health_check():
    """
    Endpoint to check the health status of the service.
    Returns `{"status": "ok"}` if the service is running.
    """
    logger.info("Health check endpoint accessed.")
    return HealthStatus(status="ok")

@app.post(
    "/generate",
    tags=["Generation"],
    summary="Generate response using Gemini",
    response_model=GeminiResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Invalid input provided"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse, "description": "Internal server error or API communication failure"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ErrorResponse, "description": "Gemini service not configured or unavailable"},
    }
)
async def generate_response(payload: PromptInput):
    """
    Accepts a user prompt, combines it with the system prompt,
    and generates a response using the configured Google Gemini model.
    """
    # Check if Gemini API is configured and model is initialized
    if not API_KEY:
        logger.error("Generate request failed: GOOGLE_API_KEY is not configured.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini API key not configured. Service is unavailable."
        )
    if not gemini_model:
        logger.error("Generate request failed: Gemini model is not initialized.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini model not initialized. Service is unavailable."
        )

    user_prompt = payload.user_prompt.strip()
    if not user_prompt:
         # This check is technically redundant due to Pydantic's min_length, but good for clarity
        logger.warning("Generate request failed: 'user_prompt' is empty.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'user_prompt' must be a non-empty string."
        )

    logger.info(f"Received user prompt: {user_prompt[:100]}...")

    # Combine system and user prompts
    # Note: For more complex interactions, consider using the Chat history features of the Gemini API if applicable.
    full_prompt = f"{SYSTEM_PROMPT}\n\nUser: {user_prompt}\nAssistant:"
    logger.debug(f"Full prompt being sent to Gemini: {full_prompt[:200]}...")

    try:
        # Call the Gemini API (using async version if available and needed)
        # response = await gemini_model.generate_content_async(full_prompt) # If using async everywhere
        logger.info(f"Sending request to Gemini model: {MODEL_NAME}")
        response = gemini_model.generate_content(full_prompt)

        # --- Safety Handling ---
        if not response.parts:
            block_reason = "Unknown safety block"
            try:
                # Accessing prompt_feedback might raise an exception if it doesn't exist
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                    block_reason = response.prompt_feedback.block_reason.name
            except ValueError:
                 logger.warning("Could not retrieve block reason from prompt_feedback.")

            logger.warning(f"Gemini response was blocked. Reason: {block_reason}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, # Or 500 depending on policy
                detail=f"Response blocked due to safety concerns ({block_reason}). Please modify your prompt."
            )

        # Extract the text response
        result_text = response.text
        logger.info("Successfully received response from Gemini.")
        logger.debug(f"Gemini response text: {result_text[:200]}...")

        return GeminiResponse(response=result_text)

    except HTTPException as http_exc:
        # Re-raise HTTPExceptions (like the safety block one)
        raise http_exc
    except Exception as e:
        logger.error(f"Error calling Google Gemini API: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while communicating with the Gemini API."
        )

# --- Run the App (for local development) ---
if __name__ == '__main__':
    # Use port 8000 for FastAPI convention, can be changed
    uvicorn.run("main:app", host='0.0.0.0', port=8000, reload=True)
