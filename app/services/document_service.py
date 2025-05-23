"""
Document processing services: PDF processing, chunking, and vector indexing.
"""
import os
import shutil
from typing import List, Optional
from langchain.schema import Document
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.logging_config import logger
from app.core.config import FAISS_INDEX_DIR, UPLOADS_DIR, RAG_TOP_K, CURRENT_PDF_NAME
from app.models_init import get_models


def load_and_chunk_pdf(pdf_file_path: str) -> List[str]:
    """
    Load a PDF file and split it into text chunks.
    
    Args:
        pdf_file_path: Path to the PDF file
        
    Returns:
        List of text chunks
    """
    try:
        from PyPDF2 import PdfReader
        
        logger.info(f"Loading and chunking PDF: {pdf_file_path}")
        
        reader = PdfReader(pdf_file_path)
        all_text = ""
        
        for page in reader.pages:
            text = page.extract_text()
            if text:
                all_text += text + "\n"
        
        # Split the text into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,  # Increased size for better context
            chunk_overlap=100,  # Increased overlap to maintain context
            separators=["\n\n", "\n", ".", " ", ""]  # Improved splitting hierarchy
        )
        chunks = text_splitter.split_text(all_text)
        
        logger.info(f"PDF processed into {len(chunks)} chunks")
        return chunks
    
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        raise


def create_or_update_faiss_index(chunks: List[str], pdf_name: str) -> FAISS:
    """
    Create or update FAISS vector store with text chunks.
    Since we now clear the index before adding new documents, this function
    mainly creates a new index each time.
    
    Args:
        chunks: List of text chunks
        pdf_name: Name of the PDF file
        
    Returns:
        FAISS vector store
    """
    try:
        logger.info(f"Creating FAISS index for {pdf_name}")
        
        # Get embeddings model
        models = get_models()
        embeddings = models["embeddings"]
        
        if embeddings is None:
            raise ValueError("Embeddings model not initialized")
        
        # Ensure directory exists
        os.makedirs(FAISS_INDEX_DIR, exist_ok=True)
        
        # Convert chunks to Document objects with enhanced metadata
        documents = [
            Document(
                page_content=chunk, 
                metadata={
                    "source": pdf_name, 
                    "chunk_id": i,
                    "document_name": pdf_name
                }
            ) 
            for i, chunk in enumerate(chunks)
        ]
        
        # Create FAISS vector store from documents
        vectorstore = FAISS.from_documents(documents, embeddings)
        
        # Save the vector store to disk
        vectorstore.save_local(folder_path=str(FAISS_INDEX_DIR))
        logger.info(f"FAISS index created and saved to {FAISS_INDEX_DIR}")
        
        # Update the current PDF name in the config
        global CURRENT_PDF_NAME
        CURRENT_PDF_NAME = pdf_name
        
        return vectorstore
    
    except Exception as e:
        logger.error(f"Error creating FAISS index: {e}")
        raise


def query_faiss_index(query: str, top_k: int = RAG_TOP_K) -> List[str]:
    """
    Query FAISS vector store for relevant chunks.
    
    Args:
        query: Query text
        top_k: Number of results to return
        
    Returns:
        List of relevant text chunks or empty list if no index exists
    """
    try:
        logger.info(f"Querying FAISS index for: '{query}'")
        
        # Get embeddings model
        models = get_models()
        embeddings = models["embeddings"]
        
        if embeddings is None:
            raise ValueError("Embeddings model not initialized")
        
        # Check if FAISS index exists
        if not os.path.exists(FAISS_INDEX_DIR) or not os.path.exists(os.path.join(FAISS_INDEX_DIR, "index.faiss")):
            logger.info("No FAISS index found. Returning empty context.")
            return []
        
        # Load the vector store
        vectorstore = FAISS.load_local(
            folder_path=str(FAISS_INDEX_DIR), 
            embeddings=embeddings,
            allow_dangerous_deserialization=True
        )
        
        # Perform similarity search
        results = vectorstore.similarity_search(query, k=top_k)
        
        # Extract the text content from Document objects
        relevant_chunks = [doc.page_content for doc in results]
        
        logger.info(f"Retrieved {len(relevant_chunks)} relevant chunks from FAISS index")
        return relevant_chunks
    
    except Exception as e:
        logger.error(f"Error querying FAISS index: {e}")
        # Return empty list instead of raising exception
        logger.info("Returning empty context due to error")
        return []


def process_and_index_pdf(pdf_path: str, filename: str) -> bool:
    """
    Process a PDF file and index it in FAISS.
    On each new PDF upload, previous documents are cleared to avoid context mixing.
    
    Args:
        pdf_path: Path to the uploaded PDF file
        filename: Original filename of the PDF
        
    Returns:
        True if successful
    """
    try:
        logger.info(f"Processing and indexing PDF: {filename}")
        
        # Clear existing index if it exists
        if os.path.exists(FAISS_INDEX_DIR):
            logger.info("Clearing existing FAISS index before adding new document")
            shutil.rmtree(FAISS_INDEX_DIR)
            os.makedirs(FAISS_INDEX_DIR, exist_ok=True)
        
        # Load and chunk the PDF
        chunks = load_and_chunk_pdf(pdf_path)
        
        # Create new FAISS index (no need to update since we cleared it)
        create_or_update_faiss_index(chunks, filename)
        
        logger.info(f"PDF '{filename}' processed and indexed successfully")
        return True
    
    except Exception as e:
        logger.error(f"Error processing and indexing PDF: {e}")
        raise


def clear_faiss_index() -> bool:
    """
    Clear the FAISS index and reset the current document name.
    Used when a user refreshes the page to start with a fresh state.
    
    Returns:
        True if successful, False if there was no index to clear
    """
    try:
        global CURRENT_PDF_NAME
        
        if os.path.exists(FAISS_INDEX_DIR):
            logger.info("Clearing existing FAISS index")
            shutil.rmtree(FAISS_INDEX_DIR)
            os.makedirs(FAISS_INDEX_DIR, exist_ok=True)
            
            # Reset the current PDF name
            CURRENT_PDF_NAME = None
            
            logger.info("FAISS index cleared successfully")
            return True
        else:
            logger.info("No FAISS index to clear")
            return False
            
    except Exception as e:
        logger.error(f"Error clearing FAISS index: {e}")
        raise