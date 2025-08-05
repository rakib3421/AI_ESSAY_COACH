"""
AI module for the Essay Revision Application
Contains all AI-related functions for essay analysis and feedback generation
"""
import openai
import json
import time
import logging
import re
import datetime
from config import Config
from db import save_analysis_to_db, save_step_wise_checklist

# Import caching if available
try:
    from cache import get_cached_analysis, cache_analysis, get_cache_stats
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    logging.warning("Caching not available, analysis results will not be cached")

# Set up logging
logger = logging.getLogger(__name__)

# OpenAI configuration
openai.api_key = Config.OPENAI_API_KEY

# Initialize OpenAI client for the new API format
try:
    from openai import OpenAI
    client = OpenAI(api_key=Config.OPENAI_API_KEY)
except ImportError:
    # Fallback for older openai library
    client = None
    logger.warning("Using legacy OpenAI API format")

def make_openai_request(messages, model="gpt-4o-mini", temperature=0, max_retries=3, retry_delay=2):
    """
    Make OpenAI API request with retry logic and comprehensive error handling
    
    Args:
        messages (list): List of messages for the conversation
        model (str): Model to use
        temperature (float): Temperature for randomness
        max_retries (int): Maximum number of retry attempts
        retry_delay (int): Delay between retries in seconds
    
    Returns:
        str or None: Response content or None if failed
    """
    for attempt in range(max_retries):
        try:
            if client:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    timeout=60  # 60 second timeout
                )
            else:
                # Fallback for legacy API
                response = openai.ChatCompletion.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    request_timeout=60
                )
            
            return response.choices[0].message.content
        
        except openai.RateLimitError as e:
            logger.warning(f"OpenAI rate limit exceeded (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                logger.info(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            else:
                logger.error("Rate limit exceeded after all retries")
                return None
        
        except openai.APITimeoutError as e:
            logger.warning(f"OpenAI API timeout (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                logger.error("API timeout after all retries")
                return None
        
        except openai.APIConnectionError as e:
            logger.warning(f"OpenAI API connection error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                logger.error("API connection error after all retries")
                return None
        
        except openai.AuthenticationError as e:
            logger.error(f"OpenAI authentication error: {e}")
            return None  # Don't retry authentication errors
        
        except openai.BadRequestError as e:
            logger.error(f"OpenAI bad request error: {e}")
            return None  # Don't retry bad request errors
        
        except Exception as e:
            logger.warning(f"Unexpected OpenAI API error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                logger.error("Unexpected API error after all retries")
                return None
    
    return None

def generate_fallback_analysis(essay_text, essay_type):
    """
    Generate a basic fallback analysis when AI API fails
    
    Args:
        essay_text (str): The essay text
        essay_type (str): Type of essay
    
    Returns:
        dict: Basic analysis structure
    """
    logger.info("Generating fallback analysis due to AI API failure")
    
    # Basic word count and sentence analysis
    word_count = len(essay_text.split())
    sentence_count = len([s for s in essay_text.split('.') if s.strip()])
    paragraph_count = len([p for p in essay_text.split('\n\n') if p.strip()])
    
    # Generate basic scores based on essay structure
    base_score = 70  # Default base score
    
    # Adjust scores based on essay length and structure
    if word_count < 200:
        length_modifier = -15
    elif word_count < 400:
        length_modifier = -5
    elif word_count > 800:
        length_modifier = 5
    else:
        length_modifier = 0
    
    scores = {
        'ideas': max(50, min(100, base_score + length_modifier)),
        'organization': max(50, min(100, base_score + (paragraph_count * 2))),
        'style': max(50, min(100, base_score)),
        'grammar': max(50, min(100, base_score + 5))
    }
    
    fallback_analysis = {
        'essay_type': essay_type,
        'scores': scores,
        'score_reasons': {
            'ideas': 'Basic analysis - AI service temporarily unavailable',
            'organization': f'Essay has {paragraph_count} paragraphs',
            'style': 'Unable to analyze style - AI service unavailable',
            'grammar': 'Basic grammar check - full analysis unavailable'
        },
        'suggestions': [
            {
                'type': 'general',
                'text': 'AI analysis temporarily unavailable',
                'reason': 'Please try again later for detailed feedback'
            }
        ],
        'examples': {
            'ideas': ['AI analysis unavailable'],
            'organization': ['Basic structure detected'],
            'style': ['Style analysis unavailable'],
            'grammar': ['Grammar analysis unavailable']
        },
        'tagged_essay': essay_text,
        'word_suggestions': [],
        'fallback_used': True
    }
    
    logger.warning("Fallback analysis generated due to AI API failure")
    return fallback_analysis

def detect_essay_type(essay_text):
    """Detect the type of essay using AI with fallback"""
    content = f"""
    Analyze the following essay and determine its type. Choose from:
    - argumentative
    - narrative
    - literary
    - expository
    - descriptive
    - compare

    Essay: {essay_text[:1000]}...

    Respond with only the essay type in lowercase.
    """
    
    try:
        messages = [{"role": "user", "content": content}]
        response_content = make_openai_request(messages, temperature=0)
        
        if response_content:
            essay_type = response_content.strip().lower()
            valid_types = ['argumentative', 'narrative', 'literary', 'expository', 'descriptive', 'compare']
            if essay_type in valid_types:
                logger.info(f"Essay type detected: {essay_type}")
                return essay_type
            else:
                logger.warning(f"Invalid essay type detected: {essay_type}, defaulting to expository")
                return 'expository'
        else:
            logger.warning("Failed to detect essay type, defaulting to expository")
            return 'expository'
    
    except Exception as e:
        logger.error(f"Essay type detection error: {e}")
        return 'expository'

def get_essay_specific_prompt(essay_type, coaching_level):
    """Get essay-specific prompts based on type and coaching level"""
    base_prompts = {
        'argumentative': {'focus': 'thesis strength, evidence quality, counterarguments, logical flow, source credibility',
                         'specific_checks': ['Check if thesis is clear and debatable', 'Verify evidence supports claims',
                                           'Look for counterargument acknowledgment', 'Check for logical fallacies',
                                           'Verify source authenticity (flag Wikipedia usage)']},
        'narrative': {'focus': 'story structure, character development, dialogue, imagery, pacing',
                     'specific_checks': ['Check narrative arc completeness', 'Evaluate dialogue authenticity',
                                       'Assess descriptive imagery', 'Check chronological flow',
                                       'Evaluate emotional engagement']},
        'literary': {'focus': 'thesis about literature, textual evidence, present tense usage, title formatting',
                    'specific_checks': ['Ensure titles are italicized properly', 'Check for present tense consistency',
                                      'Verify quotes are embedded properly', 'Check for literary analysis depth',
                                      'Verify textual evidence supports claims']},
        'expository': {'focus': 'clear explanation, logical organization, factual accuracy, examples',
                      'specific_checks': ['Check clarity of explanations', 'Verify logical organization',
                                        'Check for adequate examples', 'Verify factual accuracy',
                                        'Check for clear topic sentences']},
        'descriptive': {'focus': 'sensory details, vivid imagery, spatial organization, mood creation',
                       'specific_checks': ['Check for sensory detail variety', 'Evaluate imagery vividness',
                                         'Check spatial organization', 'Assess mood consistency',
                                         'Check for show vs tell balance']},
        'compare': {'focus': 'clear comparison criteria, balanced analysis, transition words, conclusion synthesis',
                   'specific_checks': ['Check comparison criteria clarity', 'Verify balanced treatment of subjects',
                                     'Check for effective transitions', 'Evaluate synthesis in conclusion',
                                     'Check for point-by-point or block organization']}
    }
    
    intensity_levels = {
        'light': 'Provide gentle suggestions focusing on the most critical issues only.',
        'medium': 'Provide moderate feedback covering important issues with some detail.',
        'intensive': 'Provide comprehensive feedback with detailed explanations for all issues found.'
    }
    
    essay_info = base_prompts.get(essay_type, base_prompts['expository'])
    intensity = intensity_levels.get(coaching_level, intensity_levels['medium'])
    
    return essay_info, intensity

def analyze_essay_with_ai(essay_text, essay_type='auto', coaching_level='medium', suggestion_aggressiveness='medium'):
    """
    Analyze essay using AI and return comprehensive feedback
    Uses caching to avoid redundant API calls for identical essays
    """
    # Import performance monitoring
    try:
        from performance_monitor import AIAnalysisTimer
        MONITORING_AVAILABLE = True
    except ImportError:
        MONITORING_AVAILABLE = False
    
    # Check cache first if available
    if CACHE_AVAILABLE:
        cached_result = get_cached_analysis(essay_text, essay_type, coaching_level, suggestion_aggressiveness)
        if cached_result:
            logger.info("Returning cached analysis result")
            # Record cache hit
            if MONITORING_AVAILABLE:
                with AIAnalysisTimer(was_cached=True):
                    pass  # Just record the cache hit
            return cached_result
    
    # Perform AI analysis with performance monitoring
    analysis_context = AIAnalysisTimer(was_cached=False) if MONITORING_AVAILABLE else None
    
    if analysis_context:
        analysis_context.__enter__()
    
    try:
        # Perform AI analysis
        logger.info(f"Performing new AI analysis for essay type: {essay_type}, coaching: {coaching_level}, aggressiveness: {suggestion_aggressiveness}")
        
        if essay_type == 'auto':
            essay_type = detect_essay_type(essay_text)
        
        essay_info, intensity = get_essay_specific_prompt(essay_type, coaching_level)
    
    # Map aggressiveness to descriptive text for prompt with explicit instructions and examples
    aggressiveness_map = {
        'low': (
            'Provide minimal, gentle suggestions focusing only on the most critical issues. ' 
            'Avoid overwhelming the student with too many corrections. ' 
            'Limit suggestions to 3 or fewer major points. ' 
            'Example: Point out only major grammar mistakes or unclear sentences.'
        ),
        'medium': (
            'Provide moderate feedback covering important issues with some detail. ' 
            'Balance between helpful suggestions and preserving student voice. ' 
            'Limit suggestions to 5-7 points including word choice and sentence structure improvements. ' 
            'Example: Suggest improvements in word choice, sentence structure, and flow.'
        ),
        'high': (
            'Provide comprehensive and detailed feedback covering all possible improvements. ' 
            'Include minor stylistic and grammatical suggestions to refine the essay fully. ' 
            'Provide 10 or more detailed suggestions including minor punctuation and phrasing. ' 
            'Example: Highlight even small punctuation errors and suggest alternative phrasing.'
        )
    }
    aggressiveness_text = aggressiveness_map.get(suggestion_aggressiveness.lower(), aggressiveness_map['medium'])
    
    # Compose prompt with system message style for clarity
    content = f"""
You are an expert writing coach focused on helping students improve their writing through specific, actionable suggestions.

Your role is to provide precise, granular feedback that helps students learn to self-correct. Focus on preserving the student's voice while enhancing clarity, correctness, and style.

CRITICAL INSTRUCTIONS:

1. Use inline tags ONLY for specific text that needs correction:
   - <delete>word</delete> for words to be removed
   - <add>word</add> for words to be added  
   - <replace>old_word|new_word</replace> for word substitutions

2. For each suggestion, provide a clear, educational explanation in the "reason" field explaining WHY the change improves the writing.

3. Provide scores (0-100) for: ideas, organization, style, grammar
4. Provide score explanations in "score_reasons"
5. Provide 2 specific examples per rubric dimension in "examples"

EXAMPLE OF GOOD SUGGESTIONS:
Input: "He is a goodest player in the team. He do practice every day."
Output: 
- <replace>goodest|best</replace> (reason: "Use 'best' instead of 'goodest' - 'good' becomes 'best' in superlative form")
- <replace>do|does</replace> (reason: "Use 'does' with 'he' - third person singular requires 'does'")

Focus on these common student errors:
- Grammar: subject-verb agreement, tense consistency, article usage
- Style: word choice, sentence variety, clarity
- Mechanics: punctuation, capitalization

COACHING INTENSITY: {intensity}
SUGGESTION LEVEL: {aggressiveness_text}

Essay Type Focus: {essay_info['focus']}
Specific Checks: {', '.join(essay_info['specific_checks'])}

Return ONLY valid JSON with this structure:
{{
    "tagged_essay": "essay with inline tags",
    "scores": {{"ideas": 85, "organization": 80, "style": 75, "grammar": 90}},
    "score_reasons": {{"ideas": "Clear main points...", "organization": "Good structure...", "style": "Engaging voice...", "grammar": "Few errors..."}},
    "suggestions": [
        {{"type": "replace", "text": "goodest -> best", "reason": "Use 'best' instead of 'goodest' - superlative form"}}
    ],
    "examples": {{"ideas": ["Strong thesis", "Clear evidence"], "organization": ["Good transitions", "Logical flow"], "style": ["Varied sentences", "Engaging tone"], "grammar": ["Correct tenses", "Proper punctuation"]}}
}}

Essay to analyze:
{essay_text[:5000]}
"""
    
    try:
        start_time = time.time()
        logger.info(f"Starting AI analysis for essay of length {len(essay_text)} characters with aggressiveness {suggestion_aggressiveness}")
        
        # Check if OpenAI API key is configured
        if not Config.OPENAI_API_KEY:
            logger.error("OpenAI API key not configured")
            return generate_fallback_analysis(essay_text, essay_type)
        
        messages = [{"role": "user", "content": content}]
        response_text = make_openai_request(
            messages=messages,
            model="gpt-4",
            temperature=0.6,
            max_retries=3
        )
        
        if not response_text:
            logger.warning("OpenAI API request failed, using fallback analysis")
            return generate_fallback_analysis(essay_text, essay_type)
            
        response_time = time.time() - start_time
        logger.info(f"AI analysis completed in {response_time:.2f} seconds")

        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0]
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0]
        
        # Clean and validate JSON response
        response_text = response_text.strip()
        if not response_text:
            logger.warning("Empty response from AI, using fallback")
            return generate_fallback_analysis(essay_text, essay_type)
        
        logger.debug(f"Raw AI response (first 500 chars): {response_text[:500]}")
        
        try:
            analysis_data = json.loads(response_text)
        except json.JSONDecodeError as json_error:
            logger.error(f"JSON parsing failed: {json_error}")
            logger.error(f"Raw response: {response_text}")
            # Try to extract JSON from response if it contains extra text
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    analysis_data = json.loads(json_match.group())
                    logger.info("Successfully extracted JSON from response")
                except:
                    logger.warning("Could not parse AI response, using fallback")
                    return generate_fallback_analysis(essay_text, essay_type)
            else:
                logger.warning("No JSON found in AI response, using fallback")
                return generate_fallback_analysis(essay_text, essay_type)

        # Validate analysis data structure
        if not isinstance(analysis_data, dict):
            logger.warning("AI response is not a dictionary, using fallback")
            return generate_fallback_analysis(essay_text, essay_type)

        # Log suggestions and reasons for debugging
        if 'suggestions' in analysis_data:
            for i, suggestion in enumerate(analysis_data['suggestions']):
                logger.debug(f"Suggestion {i}: type={suggestion.get('type')}, text={suggestion.get('text')}, reason={suggestion.get('reason')}")

        # Ensure scores exist and are valid
        if 'scores' not in analysis_data or not isinstance(analysis_data['scores'], dict):
            logger.warning("Invalid scores in AI response")
            analysis_data['scores'] = {'ideas': 75, 'organization': 75, 'style': 75, 'grammar': 75}
        else:
            # Validate each score is between 0 and 100
            for key in ['ideas', 'organization', 'style', 'grammar']:
                val = analysis_data['scores'].get(key, 75)
                if not isinstance(val, (int, float)) or val < 0 or val > 100:
                    logger.warning(f"Invalid score for {key}: {val}, setting to 75")
                    analysis_data['scores'][key] = 75

        # Ensure score reasons exist
        if 'score_reasons' not in analysis_data:
            analysis_data['score_reasons'] = {
                'ideas': 'No reason provided.',
                'organization': 'No reason provided.',
                'style': 'No reason provided.',
                'grammar': 'No reason provided.'
            }
        else:
            for key in ['ideas', 'organization', 'style', 'grammar']:
                if key not in analysis_data['score_reasons']:
                    analysis_data['score_reasons'][key] = 'No reason provided.'

        if 'tagged_essay' not in analysis_data:
            analysis_data['tagged_essay'] = essay_text
        
        if 'suggestions' not in analysis_data:
            analysis_data['suggestions'] = []
        else:
            # Ensure each suggestion has a reason
            for suggestion in analysis_data['suggestions']:
                if 'reason' not in suggestion or not suggestion['reason'].strip():
                    # Auto-generate default reason based on suggestion type
                    stype = suggestion.get('type', '').lower()
                    if stype == 'delete':
                        suggestion['reason'] = 'This word is unnecessary or incorrect.'
                    elif stype == 'add':
                        suggestion['reason'] = 'This word improves clarity or correctness.'
                    elif stype == 'replace':
                        suggestion['reason'] = 'This word is a better choice for style or grammar.'
                    else:
                        suggestion['reason'] = 'No explanation provided by AI.'

        # Ensure examples field exists and has proper structure
        if 'examples' not in analysis_data:
            analysis_data['examples'] = {
                'ideas': [],
                'organization': [],
                'style': [],
                'grammar': []
            }
        else:
            for key in ['ideas', 'organization', 'style', 'grammar']:
                if key not in analysis_data['examples'] or not isinstance(analysis_data['examples'][key], list):
                    analysis_data['examples'][key] = []

        analysis_data['essay_type'] = essay_type.title()
        
        # Save to database and get analysis_id
        analysis_id = save_analysis_to_db(essay_text, analysis_data)
        if analysis_id:
            analysis_data['analysis_id'] = analysis_id
            logger.info(f"Analysis saved with ID: {analysis_id}")
            
            # Generate and save step-wise checklist
            checklist_steps = generate_step_wise_checklist(essay_text, essay_type, analysis_data)
            save_step_wise_checklist(analysis_id, checklist_steps)
            analysis_data['checklist_steps'] = checklist_steps
            logger.info("Step-wise checklist generated and saved")
        else:
            logger.warning("Failed to save analysis to database")
        
        # Cache the result if caching is available
        if CACHE_AVAILABLE:
            cache_analysis(essay_text, analysis_data, essay_type, coaching_level, suggestion_aggressiveness)
            logger.info("Analysis result cached for future use")
        
        return analysis_data
        
    except Exception as e:
        error_type = type(e).__name__
        logger.error(f"AI Analysis error ({error_type}): {e}")
        
        # Log more details for debugging
        if hasattr(e, 'response'):
            logger.error(f"API response details: {e.response}")
        
        logger.warning("Returning fallback analysis due to AI processing error")
        fallback = generate_fallback_analysis(essay_text, essay_type)
        fallback['error_occurred'] = True
        fallback['error_type'] = error_type
        return fallback
    
    finally:
        # Close performance monitoring context
        if analysis_context:
            analysis_context.__exit__(None, None, None)

def generate_step_wise_checklist(essay_text, essay_type, analysis_data):
    """Generate step-wise checklist based on essay analysis"""
    
    base_steps = [
        {
            'name': 'Review Thesis Statement',
            'description': 'Ensure your main argument is clear and debatable',
            'order': 1,
            'required': True,
            'criteria': 'Thesis statement identified and evaluated for clarity'
        },
        {
            'name': 'Strengthen Evidence',
            'description': 'Add or improve supporting evidence for your arguments',
            'order': 2,
            'required': True,
            'criteria': 'At least two pieces of evidence per main point'
        },
        {
            'name': 'Improve Transitions',
            'description': 'Connect paragraphs and ideas more smoothly',
            'order': 3,
            'required': True,
            'criteria': 'Clear transitions between all paragraphs'
        },
        {
            'name': 'Refine Word Choice',
            'description': 'Replace weak or repetitive words with stronger alternatives',
            'order': 4,
            'required': False,
            'criteria': 'No obvious word repetition or vague language'
        },
        {
            'name': 'Polish Grammar',
            'description': 'Correct any remaining grammatical errors',
            'order': 5,
            'required': True,
            'criteria': 'No major grammatical errors remain'
        },
        {
            'name': 'Final Review',
            'description': 'Read through entire essay for flow and coherence',
            'order': 6,
            'required': True,
            'criteria': 'Essay flows smoothly from introduction to conclusion'
        }
    ]
    
    # Customize steps based on essay type
    if essay_type.lower() == 'argumentative':
        base_steps.insert(2, {
            'name': 'Address Counterarguments',
            'description': 'Acknowledge and refute opposing viewpoints',
            'order': 3,
            'required': True,
            'criteria': 'At least one counterargument addressed'
        })
    elif essay_type.lower() == 'narrative':
        base_steps[1] = {
            'name': 'Develop Characters',
            'description': 'Ensure characters are well-developed and believable',
            'order': 2,
            'required': True,
            'criteria': 'Main characters have clear motivations and development'
        }
    elif essay_type.lower() == 'literary':
        base_steps.insert(1, {
            'name': 'Check Citations',
            'description': 'Verify all quotes are properly cited and integrated',
            'order': 2,
            'required': True,
            'criteria': 'All textual evidence properly cited and explained'
        })
    
    # Unlock first step by default
    for i, step in enumerate(base_steps):
        step['unlocked'] = (i == 0)
        step['completed'] = False
    
    return base_steps

def get_hybrid_essay_checks(essay_text):
    """Detect and return checks for hybrid essay types"""
    try:
        content = f"""
        Analyze this essay and determine if it contains elements from multiple essay types.
        Return a JSON object with:
        - primary_type: the main essay type
        - secondary_types: list of other detected types
        - hybrid_checks: specific checks to apply for this combination
        
        Essay: {essay_text[:1000]}...
        
        Return only valid JSON.
        """
        
        if client:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": content}],
                temperature=0
            )
        else:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": content}],
                temperature=0
            )
        
        result = json.loads(response.choices[0].message.content)
        return result
        
    except Exception as e:
        logger.error(f"Hybrid essay detection error: {e}")
        return {
            'primary_type': 'expository',
            'secondary_types': [],
            'hybrid_checks': []
        }
