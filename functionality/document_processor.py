"""Document Processing Module for ResearchGPT Assistant"""

import PyPDF2
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import os
import re
import logging

class DocumentProcessor:
    def __init__(self, config):
        """Initialize Document Processor"""
        self.config = config
        # Initialize TfidfVectorizer with appropriate parameters
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words='english',
            ngram_range=(1,2),
            min_df=1,
            max_df=0.8,
            lowercase=True,
            strip_accents='ascii'
        )  
        
        # Create document storage structure
        self.documents = {}  # Store as: {doc_id: {'title': '', 'chunks': [], 'metadata': {}}}
        self.document_vectors = None  # Store TF-IDF vectors
        self.chunk_to_doc_mapping = {}
        self.all_chunks = {}

        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def extract_text_from_pdf(self, pdf_path):
        """
        Extract text from PDF file
        
        Args:
            pdf_path (str): Path to PDF file
            
        Returns:
            str: Extracted and cleaned text
        """
        # Implement PDF text extraction
        extracted_text = ""
        
        try:
            # Open and read PDF file
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)

                # Extract text from all pages
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()

                    if page_text:
                        extracted_text += page_text +"\n\n"
                
                self.logger.info(f"Successfully extracted text from {pdf_path}")
                self.logger.info(f"Total characters extracted: {len(extracted_text)}")
        except FileNotFoundError:
            self.logger.error(f"PDF file not found {pdf_path}")
            return ""
        except Exception as e:
            self.logger.error(f"Error extracting text from PDF {pdf_path}: {str(e)}")
            return ""
        # Basic cleaning of extracted text
        cleaned_text = self._clean_pdf_text(extracted_text)
        return cleaned_text
    
    def _clean_pdf_text(self, text):
        """
        Clean text extracted from PDF to fix common issues
        
        Args:
            text (str): Raw PDF text
            
        Returns:
            str: Cleaned text
        """
        if not text:
            return ""
        
        # Remove excessive whitespace and normalize line breaks
        text = re.sub(r'\n\s*\n', '\n\n', text)  # Multiple newlines to double newline
        text = re.sub(r'\s+', ' ', text)         # Multiple spaces to single space
        text = re.sub(r'\n\n+', '\n\n', text)   # Multiple paragraph breaks to double newline
        
        # Remove common PDF artifacts
        text = re.sub(r'\x0c', '', text)         # Form feed characters
        text = re.sub(r'â€™', "'", text)         # Fix apostrophes
        text = re.sub(r'â€œ|â€\x9d', '"', text)  # Fix quotes
        text = re.sub(r'â€"', '-', text)         # Fix dashes
        
        # Remove page numbers and headers/footers (basic heuristic)
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            # Skip very short lines that might be page numbers or artifacts
            if len(line) < 3:
                continue
            # Skip lines that are just numbers (likely page numbers)
            if line.isdigit():
                continue
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def preprocess_text(self, text):
        """
        Clean and preprocess text for better analysis
        
        Args:
            text (str): Raw extracted text
            
        Returns:
            str: Preprocessed text
        """
        if not text:
            return ""
        
        # Convert to lowercase for consistency
        cleaned_text = text.lower()
        
        # Remove special characters but keep punctuation that's meaningful
        # Keep periods, commas, question marks, exclamation marks
        cleaned_text = re.sub(r'[^\w\s\.\,\?\!\-\:\;\(\)]', ' ', cleaned_text)
        
        # Normalize whitespace
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
        
        # Remove extra periods (common in PDFs)
        cleaned_text = re.sub(r'\.{2,}', '.', cleaned_text)
        
        # Clean up sentence spacing
        cleaned_text = re.sub(r'\s*\.\s*', '. ', cleaned_text)
        cleaned_text = re.sub(r'\s*\,\s*', ', ', cleaned_text)
        
        # Remove leading/trailing whitespace
        cleaned_text = cleaned_text.strip()
        
        return cleaned_text
    
    def search_within_document(self, doc_id, query, top_k=3):
        """
        Search for similar chunks within a specific document
        
        Args:
            doc_id (str): Document identifier
            query (str): Search query
            top_k (int): Number of chunks to return
            
        Returns:
            list: List of (chunk_text, similarity_score) tuples
        """
        if doc_id not in self.documents:
            self.logger.error(f"Document {doc_id} not found")
            return []
        
        doc_chunks = self.documents[doc_id]['chunks']
        
        if not doc_chunks:
            return []
        
        try:
            # Create temporary vectorizer for this document
            temp_vectorizer = TfidfVectorizer(
                stop_words='english',
                ngram_range=(1, 2),
                lowercase=True
            )
            
            # Vectorize document chunks and query
            chunk_vectors = temp_vectorizer.fit_transform(doc_chunks)
            query_vector = temp_vectorizer.transform([query.lower()])
            
            # Calculate similarities
            similarities = cosine_similarity(query_vector, chunk_vectors).flatten()
            
            # Get top results
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            results = []
            for idx in top_indices:
                if similarities[idx] > 0:
                    results.append((doc_chunks[idx], similarities[idx]))
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error searching within document {doc_id}: {str(e)}")
            return []
    
    def save_processed_documents(self, output_dir):
        """
        Save processed document data to files
        
        Args:
            output_dir (str): Directory to save processed data
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        try:
            # Save document metadata
            metadata_file = os.path.join(output_dir, 'document_metadata.json')
            import json
            
            # Prepare serializable metadata
            serializable_docs = {}
            for doc_id, doc_data in self.documents.items():
                serializable_docs[doc_id] = {
                    'title': doc_data['title'],
                    'metadata': doc_data['metadata'],
                    'file_path': doc_data['file_path'],
                    'num_chunks': doc_data['num_chunks'],
                    'raw_text_length': doc_data['raw_text_length'],
                    'processed_text_length': doc_data['processed_text_length']
                }
            
            with open(metadata_file, 'w') as f:
                json.dump(serializable_docs, f, indent=2)
            
            # Save document statistics
            stats_file = os.path.join(output_dir, 'document_stats.json')
            stats = self.get_document_stats()
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2)
            
            # Save chunks for each document
            for doc_id, doc_data in self.documents.items():
                chunks_file = os.path.join(output_dir, f'{doc_id}_chunks.txt')
                with open(chunks_file, 'w', encoding='utf-8') as f:
                    for i, chunk in enumerate(doc_data['chunks']):
                        f.write(f"--- Chunk {i+1} ---\n")
                        f.write(chunk)
                        f.write("\n\n")
            
            self.logger.info(f"Saved processed documents to {output_dir}")
            
        except Exception as e:
            self.logger.error(f"Error saving processed documents: {str(e)}")

    def chunk_text(self, text, chunk_size=None, overlap=None):
        """
        Split text into manageable chunks
        
        Args:
            text (str): Text to chunk
            chunk_size (int): Size of each chunk
            overlap (int): Overlap between chunks
            
        Returns:
            list: List of text chunks
        """
        if chunk_size is None:
            chunk_size = self.config.CHUNK_SIZE
        if overlap is None:
            overlap = self.config.OVERLAP
            
        # Implement chunking logic
        if not text or len(text) < chunk_size:
            return [text] if text else []
        
        chunks = []
        start = 0
        
        while start < len(text):
            # Calculate end position
            end = start + chunk_size

            #If this is not the last chunk, try to end at a sentence boundary
            if end < len(text):
                # Look for sentence ending within the last 200 characters of the chunk
                sentence_end_pattern = r'[.!?]\s+'
                search_start = max(end - 200, start)

                # Find sentence boundaries in the search area
                matches = list(re.finditer(sentence_end_pattern, text[search_start:end]))

                if matches:
                    # Use the last sentence boundary found
                    last_match = matches[-1]
                    end = search_start + last_match.end()

            # Extract chunk
            chunk = text[start:end].strip()

            if chunk:    #Only add non-empty chunks
                chunks.append(chunk)

            # Move start position with overlap
            start = end - overlap

            # Ensure we don't get stuck in infinite loop
            if start <= 0 or start >= len(text):
                break

        self.logger.info(f"Created {len(chunks)} chunks from text of length {len(text)}")
        return chunks
    
    def process_document(self, pdf_path):
        """
        Process a single PDF document
        
        Args:
            pdf_path (str): Path to PDF file
            
        Returns:
            str: Document ID
        """
        # Generate document ID from filename
        doc_id = os.path.basename(pdf_path).replace('.pdf', '')
        self.logger.info(f"Processing document: {pdf_path}")

        try:
            # Step 1: Extract text from PDF
            raw_text = self.extract_text_from_pdf(pdf_path)

            if not raw_text:
                self.logger.warning(f"No text extracted from {pdf_path}")
                return doc_id
            
            # Step 2: Preprocess the text
            preprocessed_text = self.preprocess_text(raw_text)

            # Step 3: Create chunks
            chunks = self.chunk_text(preprocessed_text)

            # Step 4: Extract basic metadata
            metadata = self._extract_metadata(raw_text, pdf_path)

            # Step 5: Store in document storage
            self.documents[doc_id] = {
                'title': metadata.get('title', doc_id),
                'chunks': chunks,
                'metadata': metadata,
                'file_path': pdf_path,
                'raw_text_length': len(raw_text),
                'processed_text_length': len(preprocessed_text),
                'num_chunks': len(chunks)
            }

            self.logger.info(f"Successfully processed document {doc_id}")
            self.logger.info(f"  - Raw text length: {len(raw_text)}")
            self.logger.info(f"  - Processed text length: {len(preprocessed_text)}")
            self.logger.info(f"  - Number of chunks: {len(chunks)}")
            self.save_processed_documents("results")
        
        except Exception as e:
            self.logger.error(f"Error processing document {pdf_path}: {str(e)}")

        return doc_id
    
    def _extract_metadata(self, text, pdf_path):
        """
        Extract basic metadata from document text

        Args:
            text (str): Document text
            pdf_path (str): Path to PDF file
        
        Returns:
            dict: Metadata dictionary
        """

        metadata = {
            'file_path': pdf_path,
            'file_size': os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0,
            'text_length': len(text)
        }

        # Try to extract title (first meaningful line)
        lines = text.split('\n')
        title = None

        for line in lines[:10]: # Check first 10 lines
            line = line.strip()
            if len(line) > 10 and len(line) < 200: # Reasonable title length
                # Skip lines that look like headers or page numbers
                if not re.match(r'^[\d\s\.\-]+$', line):
                    title = line
                    break
        
        metadata['title'] = title or os.path.basename(pdf_path).replace('.pdf', '')

        # Extract some basic text statistics
        words = text.split()
        metadata['word_count'] = len(words)
        metadata['estimated_pages'] = len(words) // 250 # Rough estimate 250 words per page

        return metadata

    def build_search_index(self):
        """ Build TF-IDF search index for all documents """

        if not self.documents:
            self.logger.warning("No documents to index")
            return

        self.logger.info("Building search index...")

        # Collect all chunks from all documents
        self.all_chunks = []
        self.chunk_to_doc_mapping = []

        for doc_id, doc_data in self.documents.items():
            for chunk in doc_data['chunks']:
                self.all_chunks.append(chunk)
                self.chunk_to_doc_mapping.append(doc_id)
        
        if not self.all_chunks:
            self.logger.warning("No text chunks found to index")
            return
        
        try:
            # Fit TF-IDF vectorizer and transform chunks
            self.document_vectors = self.vectorizer.fit_transform(self.all_chunks)

            self.logger.info(f"Successfully built search index")
            self.logger.info(f"  - Total chunks indexed: {len(self.all_chunks)}")
            self.logger.info(f"  - Vocabulary size: {len(self.vectorizer.vocabulary_)}")
            self.logger.info(f"  - Vector shape: {self.document_vectors.shape}")
        
        except Exception as e:
            self.logger.error(f"Error building search index: {str(e)}")
        
    def find_similar_chunks(self, query, top_k=5):
        """
        Find most similar document chunks to query using cosine similarity
        
        Args:
            query (str): Search query
            top_k (int): Number of similar chunks to return
            
        Returns:
            list: List of (chunk_text, similarity_score, doc_id) tuples
        """
        
        if not query.strip():
            self.logger.warning("Empty query provided")
            return []
        
        try:
            # Transform query using fitted vectorizer
            query_vector = self.vectorizer.transform([query.lower()])

            # Calculate cosine similarity with all document chunks
            similarities = cosine_similarity(query_vector, self.document_vectors).flatten()

            # Get top-k most similar chunks
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            # Build results
            similar_chunks = []
            for idx in top_indices:
                if similarities[idx] > 0: # Only include chunks with positive similarity
                    chunk_text = self.all_chunks[idx]
                    similarity_score = similarities[idx]
                    doc_id = self.chunk_to_doc_mapping[idx]

                    similar_chunks.append((chunk_text, similarity_score, doc_id))
            self.logger.info(f"Found {len(similar_chunks)} similar chunks for query: '{query[:50]}...'")

            return similar_chunks
        except Exception as e:
            self.logger.error(f"Error finding similar chunks: {str(e)}")
            return []
    
    def get_document_stats(self):
        """
        Get statistics about processed documents
        
        Returns:
            dict: Document statistics
        """
        
        if not self.documents:
            return {
                'num_documents': 0,
                'total_chunks': 0,
                'avg_document_length': 0,
                'document_titles': []
            }
        
        total_chunks = sum(doc['num_chunks'] for doc in self.documents.values())
        total_text_length = sum(doc['processed_text_length'] for doc in self.documents.values())
        avg_length = total_text_length / len(self.documents) if self.documents else 0

        document_titles = [doc['title'] for doc in self.documents.values()]

        stats = {
            'num_documents': len(self.documents),
            'total_chunks': total_chunks,
            'avg_document_length': avg_length,
            'total_text_length':total_text_length,
            'document_titles': document_titles,
            'document_ids': list(self.documents.keys()),
            'avg_chunks_per_doc': total_chunks / len(self.documents) if self.documents else 0,
        }
          
        return stats
    
    def get_document_by_id(self, doc_id):
        """
        Retrieve document data by ID

        Args:
            doc_id (str): Document identifier
        
        Returns:
            dict: Document data or None if not found
        """
        return self.documents.get(doc_id, None)