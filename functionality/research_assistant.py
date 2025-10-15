"""Main ResearchGPT Assistant Class"""

from mistralai import Mistral
import json
import time
import logging
from typing import List, Dict, Any, Tuple, Optional

class ResearchGPTAssistant:
    def __init__(self, config, document_processor):
        """
        Initialize ResearchGPT Assistant
        
        Args:
            config: Configuration object with API keys and settings
            document_processor: DocumentProcessor instance for socument operations
        """
        self.config = config
        self.doc_processor = document_processor
        
        # Initialize Mistral client
        self.mistral_client = Mistral(api_key=self.config.MISTRAL_API_KEY)
        
        # Initialize conversation tracking
        self.conversation_history = []

        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Track API usage
        self.api_calls_made = 0
        self.total_tokens_used = 0
        
        # Load prompt templates
        self.prompts = self._load_prompt_templates()

        self.logger.info("ResearchGPT Assistent initialized successfully")
    
    def _load_prompt_templates(self):
        """
        Load comprehensive prompt templates for different research tasks
        
        Returns:
            dict: Dictionary of prompt templates
        """
        prompts = {
            'chain_of_thought': """
You are a research assistant helping to analyze academic papers. Think through this step by step.

Research Question: {query}

Context from Research Papers:
{context}

Let's approach this systematically:

1. First, let me understand what the question is asking:
   [Analyze the question and identify key components]

2. Next, let me examine the relevant information from the papers:
   [Review and summarize key points from the context]

3. Now, let me reason through the answer step by step:
   [Provide detailed reasoning for each aspect]

4. Finally, let me synthesize a comprehensive answer:
   [Combine insights into a coherent response]

Please provide a thorough, step-by-step analysis that clearly shows your reasoning process.
            """,
            
            'self_consistency': """
You are a research assistant analyzing academic papers. I want you to approach this question from a different angle than previous attempts.

Research Question: {query}

Context from Research Papers:
{context}

Consider this question carefully and provide your analysis. Focus on:
- Different aspects or perspectives not covered in other responses
- Alternative interpretations of the available evidence
- Unique insights from the research papers
- Any limitations or gaps in the current understanding

Provide a comprehensive answer that offers a fresh perspective while remaining grounded in the evidence.
            """,
            
            'react_research': """
You are conducting a research analysis using a structured approach. Follow this format:

Research Topic: {query}

Available Information: {context}

Use this structured thinking process:

Thought: [What do I need to understand or find out next?]
Action: [What should I do - analyze, search for specific info, compare, etc.]
Observation: [What did I learn from that action?]

Repeat this process until you have sufficient information to answer the question comprehensively.

End with a final summary of your findings.
            """,
            
            'document_summary': """
You are an expert research assistant. Please provide a comprehensive summary of this document.

Document Content: {content}

Your summary should include:

1. **Main Research Question/Objective**: What is the paper trying to achieve?

2. **Methodology**: How did the researchers approach the problem?

3. **Key Findings**: What are the most important results or discoveries?

4. **Conclusions**: What do the authors conclude from their work?

5. **Limitations**: What limitations does the study have?

6. **Significance**: Why is this research important?

Please structure your response clearly and focus on the most important aspects.
            """,
            
            'qa_with_context': """
You are a knowledgeable research assistant with access to academic papers. Answer the following question based on the provided context.

Question: {query}

Relevant Context from Research Papers:
{context}

Guidelines for your response:
- Base your answer primarily on the provided context
- If the context doesn't fully address the question, acknowledge this
- Cite specific findings or claims when possible
- Be precise and avoid speculation beyond what the papers support
- If there are conflicting viewpoints in the papers, mention them

Please provide a comprehensive, evidence-based answer.
            """,
            
            'verify_answer': """
You are a research quality assessor. Please evaluate the following answer for accuracy and completeness.

Original Question: {query}

Generated Answer: {answer}

Supporting Context: {context}

Please assess:

1. **Accuracy**: Is the answer factually correct based on the context?
2. **Completeness**: Does it address all aspects of the question?
3. **Evidence Support**: Is the answer well-supported by the provided context?
4. **Clarity**: Is the answer clear and well-structured?
5. **Limitations**: Are there any gaps or limitations in the answer?

Based on your assessment, provide:
- A verification score (1-10)
- Specific areas for improvement
- An improved version of the answer if needed

Focus on making the answer as accurate and helpful as possible.
            """,
            
            'basic_qa': """
You are a helpful research assistant. Please answer the following question based on the provided context from academic papers.

Question: {query}

Context: {context}

Please provide a clear, concise answer based on the information available.
            """,
            
            'workflow_conclusion': """
Based on the research workflow conducted, do we have sufficient information to provide a comprehensive answer?

Research Question: {query}
Information Gathered: {observation}

Consider:
- Is the core question addressed?
- Are there major gaps in understanding?
- Would additional research significantly improve the answer?

Respond with: YES (sufficient) or NO (need more research)
Provide a brief explanation of your decision.
            """
        }
        return prompts
    
    def _call_mistral(self, prompt: str, temperature: Optional[float] = None,
                      max_tokens: Optional[int] = None) -> str:
        """
        Make API call to Mistral
        
        Args:
            prompt (str): Prompt to send to Mistral
            temperature (float): Temperature for generation
            
        Returns:
            str: Generated response
        """
        if temperature is None:
            temperature = self.config.TEMPERATURE
        if max_tokens is None:
            max_tokens = self.config.MAX_TOKENS
        
        try:
            # Prepare the messages for Mistral API
            messages = [
                {"role": "user", "content": prompt}
            ]
            
            # Make API call using CORRECTED method
            start_time = time.time()

            # Use the correct method call
            chat_response = self.mistral_client.chat.complete(
                model=self.config.MODEL_NAME,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            # Track API usage
            self.api_calls_made += 1
            api_time = time.time() - start_time

            # Extract response text from the response
            response_text = chat_response.choices[0].message.content

            # Update token usage if available
            if hasattr(chat_response, 'usage') and chat_response.usage:
                if hasattr(chat_response.usage, 'total_tokens'):
                    self.total_tokens_used += chat_response.usage.total_tokens
                elif hasattr(chat_response.usage, 'prompt_tokens') and hasattr(chat_response.usage, 'completed'):
                    self.total_tokens_used += chat_response.usage.prompt_tokens + chat_response.usage.completed

            # Log API call
            self.logger.info(f"Mistral API call successful (took {api_time:.2f}s)")
            self.logger.debug(f"Prompt length {len(prompt)} chars")
            self.logger.debug(f"Response length: {len(response_text)} chars")

            return response_text
        except AttributeError as e:
            # Handle specific API structure erros
            self.logger.error(f"Mistral API structure error: {str(e)}")
            self.logger.error("Attempting alternative API call method...")

            try:
                # Alternative method if the first doesn't work
                chat_response = self.mistral_client.chat(
                    model=self.config.MODEL_NAME,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )

                response_text = chat_response.choices[0].message.content
                self.api_calls_made += 1
                self.logger.info("Alternative Mistral API call successful")
                return response_text
            
            except Exception as e2:
                self.logger.error(f"Alternative API method also failed: {str(e)}")
                return f"API error: Unable to connect to Mistral. Please check your API key and model name."
        except Exception as e:
            self.logger.error(f"General error calling Mistral API: {str(e)}")
            # Provide more helpful error message
            if "authentication" in str(e).lower() or "unauthorized" in str(e).lower():
                return "API error: Invalid API key. Please check your Mistral API config in config.py."
            elif "service tier capacity exceeded for this model" in str(e).lower():
                return "You have exceeded your capacity for querying current model"
            elif "model" in str(e).lower():
                return "API error: Invalid model '{self.config.MODEL_NAME}'. Please check your model name."
            else:
                return f"API Error: {str(e)}. Please check your API configuration."
    
    def chain_of_thought_reasoning(self, query: str, context_chunks: List[Tuple]) -> str:
        """
        Use Chain-of-Thought prompting for complex reasoning
        
        Args:
            query (str): Research question
            context_chunks (list): Relevant document chunks
            
        Returns:
            str: Chain-of-thought response
        """
        self.logger.info(f"Starting Chain-of-Thought reasoning for query: {query[:50]}...")

        # Build context from chunks
        context = self._build_context_from_chunks(context_chunks)

        # Build CoT prompt
        cot_prompt = self.prompts['chain_of_thought'].format(
            query=query,
            context=context
        )

        # Generate response with CoT prompting
        response = self._call_mistral(cot_prompt, temperature=self.config.TEMPERATURE)

        # Add to conversation history
        self.conversation_history.append({
            'type': 'chain_of_thought',
            'query': query,
            'response': response,
            'timestamp': time.time()
        })

        return response
    
    def self_consistency_generate(self, query: str, context_chunks: List[Tuple],
                                   num_attempts: int =3) -> str:
        """
        Generate multiple responses and select most consistent
        
        Args:
            query (str): Research question
            context_chunks (list): Relevant document chunks  
            num_attempts (int): Number of responses to generate
            
        Returns:
            str: Most consistent response
        """
        self.logger.info(f"Starting Self-Consistency generation with {num_attempts} attempts")

        responses = []
        context = self._build_context_from_chunks(context_chunks)

        # Generate multiple responses with slight temperature variation
        for i in range(num_attempts):
            # Vary temperature slightly for diversity
            temp_variation = self.config.TEMPERATURE + (i * 0.1)
            temp_variation = min(temp_variation, 1.0) # Cap at 1.0

            prompt = self.prompts['self_consistency'].format(
                query=query,
                context=context
            )

            response = self._call_mistral(prompt, temperature=temp_variation)
            responses.append(response)

            self.logger.debug(f"Generated response {i+1}/{num_attempts}")
        
        # Implement consistency checking and selection
        best_response = self._select_most_consistent_response(responses, query, context)

        # Add to conversation history
        self.conversation_history.append({
            'type': 'self_consistency',
            'query': query,
            'all_responses': responses,
            'selected_responses': best_response,
            'timestamp': time.time()
        })
        
        return best_response
    
    def _select_most_consistent_response(self, responses: List[str], query: str,
                                         context: str) -> str:
        """
        Select the most consistent response from multiple generations

        Args:
            responses (list): List of generated responses
            query (str): Original query
            context (str): context used
        
        Returns:
            str: Selected best response
        """
        if len(responses) == 1:
            return responses[0]
        
        # Filter out error responses
        valid_responses = [r for r in responses if not r.startswith("API Error:")]

        if not valid_responses:
            return responses[0] # Return first response even if it's an error
        
        if len(valid_responses) == 1:
            return valid_responses[0]
        
        # Simple heuristic: choose response with median length and most context references
        scored_responses = []

        for response in valid_responses:
            score = 0

            # Length score (prefer mdoerate length)
            length_score = 1.0 - abs(len(response) - 1000) / 2000 # Optimal around 1000 chars
            length_score = max(0, length_score)

            # Context reference score (count references to key terms)
            key_terms = query.lower().split()
            context_score = sum(1 for term in key_terms if term in response.lower())

            # Structure score (prefer well-structres responses)
            structure_score = 0
            if '1.' in response or '2.' in response: # Has enumeration
                structure_score += 0.5
            if len(response.split('\n')) > 3: # Has multiple paragraphs
                structure_score += 0.3
            
            total_score = length_score + (context_score * 0.3) + structure_score
            scored_responses.append((response, total_score))
        
        # Return response with highest score
        best_response = max(scored_responses, key=lambda x: x[1])[0]

        self.logger.info("Selected most consistent response using ensemble scoring")
        return best_response

    
    def react_research_workflow(self, query):
        """
        Implement ReAct prompting for structured research workflow
        
        Args:
            query (str): Research question
            
        Returns:
            dict: Complete research workflow with steps and final answer
        """
        self.logger.info(f"Starting ReAct research workflow for: {query[:50]}...")

        workflow_steps = []
        max_steps = 5

        # Initialize context gathering
        initial_context = self.doc_processor.find_similar_chunks(query, top_k=8)
        context_text = self._build_context_from_chunks(initial_context)

        for step in range(max_steps):
            self.logger.info(f"ReAct workflow step {step + 1}/{max_steps}")
            # Generate thought
            thought_prompt = f"""
            Research Workflow Step {step + 1}

            Research Question: {query}

            Previous Steps: {json.dumps(workflow_steps, indent=2)}

            Available Context: {context_text[:1000]}...

            What should I think about or analyze next to answer this research question?
            Provide a clear thought about what aspect needs attention.
            """

            thought = self._call_mistral(thought_prompt, temperature=0.3)

            # Determine action based on thought
            action_prompt = f"""
            Based on this thought: {thought}

            What specific action should I take? Choose from:
            - SEARCH: Look for specific information in the documents
            - ANALYZE: Examine and interpret findings
            - SYTHESIZE: Combine information to form conclusions
            - CONCLUSE: Provide final answer

            Respond with just the action and a brief description
            """

            action = self._call_mistral(action_prompt, temperature=0.2)

            # Execute the action
            observation = self._execute_react_action(action, query, context_text, workflow_steps)

            # Record workflow step
            workflow_step = {
                'step': step + 1,
                'thought': thought.strip(),
                'action': action.strip(),
                'observation': observation.strip()
            }
            
            observation = ""
            
            workflow_steps.append({
                'step': step + 1,
                'thought': thought,
                'action': action,
                'observation': observation
            })
            workflow_steps.append(workflow_step)
            
            # Check if workflow should conclude
            if self._should_conclude_workflow(observation, query) or "CONCLUDE" in action.upper():
                self.logger.info(f"ReAct workflow concluded at step {step + 1}")
                break
        
        # Generate final conclusion
        final_answer = self._generate_react_conclusion(query, workflow_steps, context_text)

        workflow_result = {
            'query': query,
            'workflow_steps': workflow_steps,
            'final_answer': final_answer,
            'total_steps': len(workflow_steps)
        }

        # Add to conversation history
        self.conversation_history.append({
            'type': 'react_workflow',
            'query': query,
            'workflow': workflow_result,
            'timestamp': time.time()
        })

        return workflow_result
    
    def _execute_react_action(self, action: str, query: str, context: str,
                              previous_steps: List[Dict]) -> str:
        """
        Execute a specific action in the ReAct workflow

        Args:
            action (str): Action to execute
            query (str): Research question
            context (str): Available context
            previous_steps (list): Previous workflow steps

        Returns:
            str: Observation from executing the action
        """
        action_upper = action.upper()

        if "SEARCH" in action_upper:
            # Search for more specific information
            search_terms = self._extract_search_terms_from_action(action)
            if search_terms:
                new_chunks = self.doc_processor.find_similar_chunks(search_terms, top_k=3)
                observation = f"Found additional information: {self._build_context_from_chunks(new_chunks[:50])}"
            else:
                observation = "Searched existing documents but no new relevant information found"
        
        elif "ANALYZE" in action_upper:
            # Analyze current information
            analyze_prompt = f"""
            Analyze the following information in the context of this research question: {query}

            Information to analyze: {context[:1500]}

            Provide key insights and patterns you observe.       
            """
            observation = self._call_mistral(analyze_prompt, temperature=0.4)

        elif "COMPARE" in action_upper:
            # Compare different aspects
            compare_prompt = f"""
            Compare different approaches, methods, or findings related to: {query}

            Available information: {context[:1500]}

            Highlight similarities, differences, and relative strengths/weaknesses.
            """
            observation = self._call_mistral(compare_prompt, temperature=0.4)
        
        elif "SYNTHESIZE" in action_upper:
            # Synthesize information
            synthesize_prompt = f"""
            Synthesize the information gathered so far to form coherent insights about : {query}

            Previous steps: {json.dumps(previous_steps, indent=2)}
            Context: {context[:1000]}

            Provide integrated insights that combine multiple pieces of information.
            """
            observation = self._call_mistral(synthesize_prompt, temperature=0.3)
        
        else:
            # Default observation
            observation = f"Executed action: {action}. Continuing analysis of available information."
        
        return observation

    def _extract_search_terms_from_action(self, action: str) -> str:
        """
        Extract search terms from an action description

        Args:
            action (str): Action description

        Returns:
            str: Extracted search terms
        """
        # Simple extraction - look for quoted terms of keywords after "search for"
        if "search for" in action.lower():
            parts = action.lower().split("search for")
            if len(parts) > 1:
                return parts[1].strip().strip('"\'')
        
        return ""
    
    def _should_conclude_workflow(self, observation: str, query: str) -> bool:
        """
        Determine if ReAct workflow has sufficient information
        
        Args:
            observation (str): Latest observation
            query (str): Research question
        
        Returns:
            bool: Whether to conclude workflow
        """
        # Use Mistral to decide if we have enough information
        conclusion_prompt = self.prompts['workflow_conclusion'].format(
            query=query,
            observation=observation
        )

        decision = self._call_mistral(conclusion_prompt, temperature=0.1)

        # Parse decision
        return "YES" in decision.upper() or "SUFFICIENT" in decision.upper()
    
    def _generate_react_conclusion(self, query: str, workflow_steps: List[Dict],
                                   context: str) -> str:
        """
        Generate final conclusion from ReAct workflow

        Args:
            query (str): Research question
            workflow_steps (list): All workflow steps
            context (str): Available context

        Returns:
            str: Final conclusion
        """

        conclusion_prompt = f"""
        Based on the structured research workflow conducted, provide a comprehensive answer to the research question

        Research Question: {query}

        Workflow Steps Completed:
        {json.dumps(workflow_steps, indent=2)}

        Original Context:
        {context[:1000]}...

        Sythesize all findings into a clear, comprehensive answer that addresses the research question directly
        """

        final_answer = self._call_mistral(conclusion_prompt, temperature=0.3)
        return final_answer
    
    def verify_and_edit_answer(self, answer: str, original_query: str,
                                context: str) -> Dict[str, Any]:
        """
        Verify answer quality and suggest improvements
        
        Args:
            answer (str): Generated answer to verify
            original_query (str): Original research question
            context (str): Document context used
            
        Returns:
            dict: Verification results and improved answer
        """
        self.logger.info("Starting answer verification and improvement process")
        
        # Build verification prompt
        verify_prompt = self.prompts['verify_answer'].format(
            query=original_query,
            answer=answer,
            context=context[:2000]
        )
        
        verification_result = self._call_mistral(verify_prompt, temperature=0.2)

        # Parse verification result and extract improvements
        improved_answer = self._extract_improved_answer(verification_result, answer)
        confidence_score = self._extract_confidence_score(verification_result)
        
        verification_data = {
            'original_answer': answer,
            'verification_result': verification_result,
            'improved_answer': improved_answer,  
            'confidence_score': confidence_score,
            'verification_timestamp': time.time()   
        }
        
        self.logger.info(f"Answer verification completed with confidence score: {confidence_score}")

        return verification_data
    
    def _extract_improved_answer(self, verification_result: str, original_answer: str) -> str:
        """
        Extract improved answer from verification result

        Args:
            verification_result (str): Verification output
            original_answer (str): Original answer

        Returns:
            str: Improved answer or original if no improvement found
        """
        # Look for improved version in verification result
        lines = verification_result.split('\n')
        improved_section = False
        improved_lines = []


        for line in lines:
            line = line.strip()
            if 'improved' in line.lower() and ('version' in line.lower() or 'answer' in line.lower):
                improved_section = True
                continue
            elif improved_section and line.strip():
                # Skip lines that look like section headers
                if not (line.strip().startswith('**') or line.strip().startswith('#')):
                    improved_lines.append(line)
        if improved_lines:
            improved_answer = '\n'.join(improved_lines).strip()
            # Only return if it's substantially different and longer than original
            if len(improved_answer) > len(original_answer) * 0.5:
                return improved_answer
        
        return original_answer

    def _extract_confidence_score(self, verification_result: str) -> float:
        """
        Extract confidence score from cerification result

        Args:
            verification_result (str): Verification output
        
        Returns:
            float: Confidence score between 0 and 1
        """
        # Look for numerical scores in the verification result
        import re

        # Look for patterns like "score: 8/10" or "8 our of 10"
        score_patterns = [
            r'score[:\s]+(\d+)(?:/10|\s*out\s*of\s*10)',
            r'(\d+)(?:/10|\s*out\s*of\s*10)',
            r'(\d+)\.(\d+)(?:/10\s*out\s*of\s*10)'
        ]

        for pattern in score_patterns:
            matches = re.findall(pattern, verification_result.lower())
            if matches:
                try:
                    if isinstance(matches[0], tuple):
                        score = float(matches[0][0] + '.' + matches[0][1])
                    else:
                        score = float(matches[0])
                    return min(score / 10.0, 1.0) # Normalize 0-1
                except ValueError:
                    continue
        
        # Default confidence based on presence of positive keywords
        positive_indicators = ['accurate', 'comprehensive', 'well-supported', 'clear']
        negative_indicators = ['inaccurate', 'incomplete', 'unclear', 'unsupported']

        positive_count = sum(1 for word in positive_indicators if word in verification_result.lower())
        negative_count = sum(1 for word in negative_indicators if word in verification_result.lower())

        # Heuristic confidence calculation
        confidence = 0.7 + (positive_count * 0.1) - (negative_count * 0.15)
        return max(0.0, min(confidence, 1.0))

    def _build_context_from_chunks(self, chunks: List[Tuple]) -> str:
        """
        Build formatted context string from document chunks

        Args:
            chunks (list): List of (text, score, doc_id) tuples

        Returns:
            str: Formatted context string
        """
        if not chunks:
            return "No relevant context found in the documents."
        
        context_parts = []
        for i, (chunk_text, score, doc_id) in enumerate (chunks):
            context_parts.append(f"Source {i+1} (from {doc_id}):\n{chunk_text}\n")
        
        return "\n".join(context_parts)


    def answer_research_question(self, query: str, use_cot: bool=True,
                                  use_verification: bool=True,
                                  strategy: str="auto") -> Dict[str, Any]:
        """
        Main method to answer research questions
        
        Args:
            query (str): Research question
            use_cot (bool): Whether to use Chain-of-Thought
            use_verification (bool): Whether to verify answer
            
        Returns:
            dict: Complete research response
        """
        self.logger.info(f"Processing research question: {query[:100]}...")

        start_time = time.time()

        # Find relevant documents
        relevant_chunks = self.doc_processor.find_similar_chunks(query, top_k=6)

        if not relevant_chunks:
            return {
                'query': query,
                'answer': "I couldn't find relevant information in the loaded documents to answer this question",
                'relevatn_documents': 0,
                'sources_used': [],
                'strategy_used': 'none',
                'processing_time': time.time() - start_time
            }
        
        # Select strategy
        if strategy == 'auto':
            strategy = self._select_best_strategy(query, relevant_chunks)

        # Generate answer using chosen strategy
        if strategy == "react":
            workflow_result = self.react_research_workflow(query)
            answer = workflow_result['final_answer']
            strategy_data = workflow_result
        elif strategy == "self_consistency":
            answer = self.self_consistency_generate(query, relevant_chunks)
            strategy_data = {'type': 'self_consistency', 'num_attempts': 3}
        elif strategy == "cot" or use_cot:
            answer = self.chain_of_thought_reasoning(query, relevant_chunks)
            strategy_data = {'type': 'chain_of_thought'}
        else:
            # Basic QA
            context = self._build_context_from_chunks(relevant_chunks)
            basic_prompt = self.prompts['basic_qa'].format(query=query, context=context)
            answer = self._call_mistral(basic_prompt)
            strategy_data = {'type': 'basic_qa'}
        
        # Verify answer if needed
        verification_data = None
        final_answer = answer
        
        if use_verification and answer and not answer.startswith("API Error:"):
            context_str = self._build_context_from_chunks(relevant_chunks)
            verification_data = self.verify_and_edit_answer(answer, query, context_str)
            final_answer = verification_data['improved_answer']

        # Compile complete response
        response = {
            'query': query,
            'answer': final_answer,
            'relevant_documents': len(relevant_chunks),
            'sources_used': [chunk[2] for chunk in relevant_chunks],
            'strategy_used': strategy,
            'strategy_data': strategy_data,
            'verification': verification_data,
            'processing_time': time.time() - start_time,
            'api_calls_made': self.api_calls_made,
            'timestamp': time.time()
        }
        if not answer.startswith("You have exceeded"):
            self.logger.info(f"Research question processed successfully in {response['processing_time']:.2f}s")
        
        return response
    
    def _select_best_strategy(self, query: str, relevant_chunks: List[Tuple]) -> str:
        """
        Automatically select the best strategy based on query characteristics

        Args:
            query (str): Research question
            relevant_chunks (list): Available context

        Returns:
            str: Selected strategy
        """
        # Analyze query complexity
        query_lower = query.lower()

        # Complex analytical questions -> ReAct
        if any(word in query_lower for word in ['compare', 'analyze', 'evaluate', 'assess', 'contrast']):
            return "react"
        
        # Questions requiring multiple perspectives -> Self-consistency
        if any(word in query_lower for word in ['different', 'various', 'multiple', 'perspectives']):
            return "self_consistency"
        
        # Complex reasoning questions -> Chain-of-Thought
        if any(word in query_lower for word in ['why', 'how', 'explain', 'reasoning', 'because']):
            return "cot"
        
        # Simple facual questions -> Basic QA
        if any(word in query_lower for word in ['whast is', 'who is', 'when', 'where']):
            return "basic"
        
        # Default to Chain-of-Thought for comprehensive analysis
        return "cot"
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """
        Get conversation history

        Returns:
            list: Conversation history
        """
        return self.conversation_history
    
    def get_api_usage_stats(self) -> Dict[str, Any]:
        """
        Get API usage statistics

        Returns:
            dict: API usage statistics
        """
        return {
            'api_calls_made': self.api_calls_made,
            'total_tokens_used': self.total_tokens_used,
            'average_tokens_per_call': self.total_tokens_used / max(1, self.api_calls_made)
        }
    
    def clear_conversation_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        self.logger.info("conversation history cleared")


