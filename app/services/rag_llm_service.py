"""
RAG and LLM services for generating responses based on context.
"""
from typing import List, Dict
from langchain.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.output_parser import StrOutputParser
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain.schema import messages as lc_messages

from app.core.logging_config import logger
from app.models_init import get_models

# Conversation memory to maintain chat history
conversation_memory = ConversationBufferMemory(
    memory_key="chat_history", 
    return_messages=True,
    output_key="answer"
)

def reset_conversation_memory():
    """
    Reset the conversation memory when a new document is loaded or page is refreshed.
    This ensures that the conversation history doesn't mix between different documents or sessions.
    
    The conversation memory is unlimited by default, storing all previous interactions
    between the user and the assistant during the current session with the current document.
    """
    global conversation_memory
    logger.info("Resetting conversation memory - clearing all message history")
    conversation_memory.clear()


def generate_response(query: str, context_chunks: List[str]) -> str:
    """
    Generate a response using LangChain with Ollama based on context chunks.
    Uses conversation history for better follow-up questions.
    If no context chunks are provided (no document uploaded), it will
    respond in a conversational manner without referencing any document.
    
    Args:
        query: User query text
        context_chunks: List of relevant document chunks for context
        
    Returns:
        Generated response text
    """
    try:
        logger.info(f"Generating response for query: '{query}'")
        
        # Get LLM model
        models = get_models()
        llm = models["llm"]
        
        if llm is None:
            raise ValueError("LLM not initialized")
        
        # Log context info
        logger.info(f"Using {len(context_chunks)} context chunks for response generation")
        
        # Check if we have any context chunks
        has_document_context = len(context_chunks) > 0
        
        # Add context to the memory
        context = "\n".join(context_chunks) if has_document_context else ""
        
        # Create prompt template based on whether we have document context
        if has_document_context:
            # Document-specific prompt
            prompt = ChatPromptTemplate.from_template("""
            You are a friendly talkative AI assistant named Friday. Use the following context to answer the user question. Keep your answer short, concise and helpful. 
            If you cannot find the answer in the context, say so. If the question refers to previous questions or answers, 
            use the chat history to understand the context.
            
            Chat history:
            {chat_history}
            
            Context:
            {context}
            
            Question: {question}
            
            Answer:
            """)
        else:
            # General conversational prompt
            prompt = ChatPromptTemplate.from_template("""
            You are a friendly talkative AI assistant named Friday. No document has been uploaded yet, so just have a friendly conversation.
            Keep your answer short, concise and helpful. If the user asks about document-specific information, politely inform them that 
            they need to upload a document first. If the question refers to previous questions or answers, 
            use the chat history to understand the context.
            
            Chat history:
            {chat_history}
            
            Question: {question}
            
            Answer:
            """)
        
        # Get chat history from memory
        chat_history = conversation_memory.load_memory_variables({})
        
        # Create formatted history string
        history_str = ""
        if "chat_history" in chat_history and chat_history["chat_history"]:
            for message in chat_history["chat_history"]:
                if isinstance(message, lc_messages.HumanMessage):
                    history_str += f"Human: {message.content}\n"
                elif isinstance(message, lc_messages.AIMessage):
                    history_str += f"AI: {message.content}\n"
        
        # Create chain with history
        chain_input = {
            "context": context,
            "question": query,
            "chat_history": history_str
        }
        
        # Run the chain
        response = prompt.format(**chain_input)
        response = llm.invoke(response)
        formatted_response = response.strip()
        
        # Save to conversation memory
        conversation_memory.save_context(
            {"question": query},
            {"answer": formatted_response}
        )
        
        logger.info(f"Generated response: '{formatted_response[:100]}...'")
        return formatted_response
    
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        raise