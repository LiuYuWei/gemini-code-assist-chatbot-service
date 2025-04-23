// src/App.js
import React, { useState, useEffect, useRef } from 'react';
import './App.css';

// Define the backend API endpoint
const API_URL = 'http://localhost:8000/generate'; // Make sure this matches your backend setup

function App() {
  const [messages, setMessages] = useState([
    // { sender: 'assistant', text: "Hello! How can I help you today?" } // Optional initial message
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const chatWindowRef = useRef(null);

  useEffect(() => {
    if (chatWindowRef.current) {
      chatWindowRef.current.scrollTop = chatWindowRef.current.scrollHeight;
    }
  }, [messages]);

  // Function to clear the chat messages
  const handleClearChat = () => {
    setMessages([]); // Reset messages to an empty array
    setError(null); // Also clear any existing error message
    // Optionally, you could add a confirmation dialog here
    // if (!window.confirm("Are you sure you want to clear the chat?")) {
    //   return;
    // }
  };

  const handleSendMessage = async () => {
    const userPrompt = inputValue.trim();
    if (!userPrompt || isLoading) {
      return;
    }

    const newUserMessage = { sender: 'user', text: userPrompt };
    // Use functional update to ensure we have the latest state
    setMessages(prevMessages => [...prevMessages, newUserMessage]);
    setInputValue('');
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ user_prompt: userPrompt }),
      });

      if (!response.ok) {
        let errorDetail = `API Error: ${response.status} ${response.statusText}`;
        try {
            const errorData = await response.json();
            errorDetail = errorData.detail || errorDetail;
        } catch (jsonError) { /* Ignore */ }
        throw new Error(errorDetail);
      }

      const data = await response.json();
      const assistantMessage = { sender: 'assistant', text: data.response };
      // Use functional update here as well
      setMessages(prevMessages => [...prevMessages, assistantMessage]);

    } catch (err) {
      console.error("API call failed:", err);
      setError(err.message || 'Failed to fetch response from the server.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="app-container">
      <div className="chat-window" ref={chatWindowRef}>
        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.sender}`}>
            <div className="message-text">{msg.text}</div>
          </div>
        ))}
        {isLoading && <div className="loading-indicator">Assistant is thinking...</div>}
        {error && <div className="error-message">{error}</div>}
      </div>

      {/* --- Input Area Modification --- */}
      <div className="input-area">
        {/* Add the Clear Chat button HERE */}
        <button
          onClick={handleClearChat}
          className="clear-button" // Add a specific class for styling
          disabled={messages.length === 0 || isLoading} // Disable if chat is empty or loading
          title="Clear Chat History" // Tooltip for accessibility
        >
          Clear {/* You can use an icon here instead */}
        </button>

        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type your message here..."
          disabled={isLoading}
        />
        <button
            onClick={handleSendMessage}
            disabled={isLoading || !inputValue.trim()}
            className="send-button" // Add class to send button for distinct styling if needed
        >
          {isLoading ? 'Sending...' : 'Send'}
        </button>
      </div>
      {/* --- End Input Area Modification --- */}

    </div>
  );
}

export default App;
