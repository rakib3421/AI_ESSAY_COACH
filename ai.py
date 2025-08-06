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

# Add essay type normalization function
def normalize_essay_type(essay_type):
    """
    Normalize essay type to standard values to fix data truncation issues
    
    Args:
        essay_type (str): Raw essay type input
    
    Returns:
        str: Normalized essay type
    """
    if not essay_type:
        return 'hybrid'
    
    essay_type_lower = essay_type.lower().strip()
    
    # Map variations to standard types
    if any(word in essay_type_lower for word in ['argument', 'persuasive', 'opinion', 'convince']):
        return 'argumentative'
    elif any(word in essay_type_lower for word in ['narrative', 'story', 'personal', 'experience']):
        return 'narrative'
    elif any(word in essay_type_lower for word in ['literary', 'literature', 'analysis', 'critique']):
        return 'literary_analysis'
    elif any(word in essay_type_lower for word in ['compare', 'contrast', 'comparison']):
        return 'comparative'
    elif any(word in essay_type_lower for word in ['expository', 'explain', 'informative', 'inform']):
        return 'expository'
    else:
        return 'hybrid'

def fix_essay_types_in_database():
    """
    Fix essay_type values in all relevant tables by normalizing them
    This function addresses data truncation issues
    """
    import pymysql
    from config import Config
    
    conn = pymysql.connect(**Config.DB_CONFIG)
    cursor = conn.cursor()
    
    print("Starting essay_type normalization...")
    
    # Fix essay_analyses table
    print("1. Fixing essay_analyses table...")
    cursor.execute("SELECT id, essay_type FROM essay_analyses WHERE essay_type IS NOT NULL")
    analyses = cursor.fetchall()
    
    fixed_analyses = 0
    for analysis_id, essay_type in analyses:
        normalized_type = normalize_essay_type(essay_type)
        if normalized_type != essay_type:
            cursor.execute(
                "UPDATE essay_analyses SET essay_type = %s WHERE id = %s",
                (normalized_type, analysis_id)
            )
            fixed_analyses += 1
    
    print(f"Fixed {fixed_analyses} essay types in essay_analyses table")
    
    # Fix assignments table
    print("2. Fixing assignments table...")
    cursor.execute("SELECT id, essay_type FROM assignments WHERE essay_type IS NOT NULL")
    assignments = cursor.fetchall()
    
    fixed_assignments = 0
    for assignment_id, essay_type in assignments:
        normalized_type = normalize_essay_type(essay_type)
        if normalized_type != essay_type:
            cursor.execute(
                "UPDATE assignments SET essay_type = %s WHERE id = %s",
                (normalized_type, assignment_id)
            )
            fixed_assignments += 1
    
    print(f"Fixed {fixed_assignments} essay types in assignments table")
    
    # Fix essays table if it exists
    print("3. Fixing essays table...")
    try:
        cursor.execute("SELECT id, essay_type FROM essays WHERE essay_type IS NOT NULL")
        essays = cursor.fetchall()
        
        fixed_essays = 0
        for essay_id, essay_type in essays:
            normalized_type = normalize_essay_type(essay_type)
            if normalized_type != essay_type:
                cursor.execute(
                    "UPDATE essays SET essay_type = %s WHERE id = %s",
                    (normalized_type, essay_id)
                )
                fixed_essays += 1
        
        print(f"Fixed {fixed_essays} essay types in essays table")
    except Exception as e:
        print(f"Essays table not found or error: {e}")
    
    conn.commit()
    conn.close()
    
    print("Essay type normalization completed!")
    print(f"Total fixes: {fixed_analyses + fixed_assignments} records updated")

# Import caching and monitoring if available
try:
    from monitoring import get_cached_analysis, cache_analysis, get_cache_stats, record_ai_analysis, generate_cache_key
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

def make_openai_request(messages, model="gpt-4o-mini", temperature=0, max_retries=3, retry_delay=2, essay_length=None):
    """
    Make OpenAI API request with retry logic and comprehensive error handling
    
    Args:
        messages (list): List of messages for the conversation
        model (str): Model to use
        temperature (float): Temperature for randomness
        max_retries (int): Maximum number of retry attempts
        retry_delay (int): Delay between retries in seconds
        essay_length (int): Length of essay for dynamic timeout adjustment
    
    Returns:
        str or None: Response content or None if failed
    """
    # Calculate dynamic timeout based on essay length
    base_timeout = 60
    if essay_length:
        if essay_length > 3000:
            timeout = 180  # 3 minutes for very long essays
        elif essay_length > 2000:
            timeout = 120  # 2 minutes for long essays
        elif essay_length > 1000:
            timeout = 90   # 1.5 minutes for medium essays
        else:
            timeout = base_timeout
        logger.info(f"Using timeout of {timeout}s for essay of {essay_length} characters")
    else:
        timeout = base_timeout
    
    for attempt in range(max_retries):
        # Progressive timeout increase for retries
        current_timeout = timeout + (attempt * 30)  # Add 30s per retry
        
        try:
            logger.info(f"OpenAI API request attempt {attempt + 1}/{max_retries} (timeout: {current_timeout}s)")
            
            if client:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    timeout=current_timeout
                )
            else:
                # Fallback for legacy API
                response = openai.ChatCompletion.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    request_timeout=current_timeout
                )
            
            logger.info(f"OpenAI API request successful on attempt {attempt + 1}")
            return response.choices[0].message.content
        
        except openai.RateLimitError as e:
            logger.warning(f"OpenAI rate limit exceeded (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                logger.info(f"Rate limited - waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            else:
                logger.error("Rate limit exceeded after all retries")
                return None
        
        except openai.APITimeoutError as e:
            logger.warning(f"OpenAI API timeout after {current_timeout}s (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                wait_time = retry_delay * 2  # Longer wait for timeouts
                logger.info(f"Timeout - waiting {wait_time} seconds before retry with extended timeout...")
                time.sleep(wait_time)
            else:
                logger.error(f"API timeout after all retries (final timeout: {current_timeout}s)")
                return None
        
        except openai.APIConnectionError as e:
            logger.warning(f"OpenAI API connection error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                wait_time = retry_delay * 2
                logger.info(f"Connection error - waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
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
    Generate a more comprehensive fallback analysis when AI API fails
    
    Args:
        essay_text (str): The essay text
        essay_type (str): Type of essay
    
    Returns:
        dict: Enhanced analysis structure with basic checks
    """
    logger.info("Generating enhanced fallback analysis due to AI API failure")
    
    # Basic text analysis
    word_count = len(essay_text.split())
    sentence_count = len([s for s in essay_text.split('.') if s.strip()])
    paragraph_count = len([p for p in essay_text.split('\n\n') if p.strip()])
    
    # Calculate average sentence length
    avg_sentence_length = word_count / max(sentence_count, 1)
    
    # Basic readability checks
    common_issues = []
    suggestions = []
    
    # Check for basic structure issues
    if paragraph_count < 3:
        common_issues.append("Essay may need more paragraphs for better organization")
        suggestions.append({
            'type': 'structure',
            'text': 'Consider adding more paragraphs',
            'reason': 'Essays typically benefit from introduction, body paragraphs, and conclusion'
        })
    
    if word_count < 300:
        common_issues.append("Essay may be too short - consider expanding ideas")
        suggestions.append({
            'type': 'length',
            'text': 'Consider expanding your essay',
            'reason': 'Essays under 300 words may not fully develop ideas'
        })
    
    if avg_sentence_length > 25:
        common_issues.append("Some sentences may be too long")
        suggestions.append({
            'type': 'sentence_length',
            'text': 'Consider breaking long sentences',
            'reason': 'Sentences over 25 words can be hard to follow'
        })
    
    # Generate scores based on structure and length
    base_score = 70
    
    # Adjust scores based on essay characteristics
    length_modifier = 0
    if word_count < 200:
        length_modifier = -20
    elif word_count < 300:
        length_modifier = -10
    elif word_count > 500:
        length_modifier = 5
    
    structure_modifier = min(paragraph_count * 3, 10)  # Up to 10 points for good structure
    
    scores = {
        'ideas': max(50, min(95, base_score + length_modifier)),
        'organization': max(50, min(95, base_score + structure_modifier)),
        'style': max(50, min(95, base_score - 5)),  # Conservative on style without AI
        'grammar': max(50, min(95, base_score))
    }
    
    # Enhanced score reasons
    score_reasons = {
        'ideas': f'Basic analysis shows {word_count} words. AI analysis unavailable - full feedback requires service connection.',
        'organization': f'Essay has {paragraph_count} paragraphs. Structure appears {"adequate" if paragraph_count >= 3 else "minimal"}. Full analysis requires AI service.',
        'style': f'Average sentence length: {avg_sentence_length:.1f} words. Style analysis unavailable without AI service.',
        'grammar': 'Basic grammar analysis unavailable - AI service required for detailed feedback.'
    }
    
    # If we found issues, adjust scores accordingly
    if len(common_issues) > 2:
        for key in scores:
            scores[key] = max(scores[key] - 10, 50)
    
    fallback_analysis = {
        'essay_type': essay_type,
        'scores': scores,
        'score_reasons': score_reasons,
        'suggestions': suggestions + [{
            'type': 'service_notice',
            'text': 'AI analysis service temporarily unavailable',
            'reason': 'Please try again in a few minutes for detailed AI-powered feedback and suggestions'
        }],
        'examples': {
            'ideas': [f'Essay contains {word_count} words'] + (['May need more development' if word_count < 300 else 'Adequate length for idea development']),
            'organization': [f'{paragraph_count} paragraphs detected'] + (['Consider adding more paragraphs' if paragraph_count < 3 else 'Basic structure present']),
            'style': [f'Average sentence length: {avg_sentence_length:.1f} words'] + (['May need sentence variety' if avg_sentence_length > 25 else 'Sentence length appears reasonable']),
            'grammar': ['Grammar analysis requires AI service', 'Please try again when service is available']
        },
        'tagged_essay': essay_text,
        'word_suggestions': [],
        'fallback_used': True,
        'analysis_notes': f'Basic analysis completed. Word count: {word_count}, Paragraphs: {paragraph_count}, Issues found: {len(common_issues)}'
    }
    
    logger.info(f"Enhanced fallback analysis generated: {word_count} words, {paragraph_count} paragraphs, {len(common_issues)} issues identified")
    return fallback_analysis

def detect_essay_type(essay_text):
    """Detect the type of essay using AI with fallback"""
    content = f"""
    Analyze the following essay and determine its type. Choose from:
    - argumentative
    - narrative
    - literary_analysis
    - hybrid

    Essay: {essay_text[:1000]}...

    Respond with only the essay type in lowercase.
    """
    
    try:
        messages = [{"role": "user", "content": content}]
        response_content = make_openai_request(messages, temperature=0)
        
        if response_content:
            essay_type = response_content.strip().lower()
            # Normalize essay type to match config
            essay_type = normalize_essay_type(essay_type)
            logger.info(f"Essay type detected: {essay_type}")
            return essay_type
        else:
            logger.warning("Failed to detect essay type, defaulting to hybrid")
            return 'hybrid'
    
    except Exception as e:
        logger.error(f"Essay type detection error: {e}")
        return 'hybrid'

def normalize_essay_type(essay_type):
    """Normalize essay type to match database schema and config"""
    from config import Config
    
    # Handle None or empty values
    if not essay_type:
        return 'hybrid'
    
    # Clean the input
    essay_type = str(essay_type).strip().lower()
    
    # Map variations to standard types
    type_mapping = {
        'literary': 'literary_analysis',
        'literary_analysis': 'literary_analysis',
        'expository': 'hybrid',
        'descriptive': 'hybrid',
        'compare': 'hybrid',
        'comparative': 'hybrid',
        'argumentative': 'argumentative',
        'narrative': 'narrative',
        'persuasive': 'argumentative',
        'informative': 'hybrid',
        'analytical': 'literary_analysis'
    }
    
    # Return mapped type or default to hybrid
    normalized_type = type_mapping.get(essay_type, 'hybrid')
    
    # Ensure it's in the valid types from config
    if normalized_type in Config.ESSAY_TYPES:
        # Additional safety check for length (assuming VARCHAR(20) or similar)
        if len(normalized_type) <= 20:
            return normalized_type
    
    # Final fallback
    return 'hybrid'

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

def analyze_essay_with_ai(essay_text, essay_type='auto', coaching_level='medium', suggestion_aggressiveness='medium', model='gpt-4o-mini'):
    """
    Analyze essay using AI and return comprehensive feedback
    Uses caching to avoid redundant API calls for identical essays
    
    Args:
        essay_text (str): The essay text to analyze
        essay_type (str): Type of essay (auto, argumentative, narrative, etc.)
        coaching_level (str): Intensity of coaching (light, medium, intensive)
        suggestion_aggressiveness (str): Level of suggestions (low, medium, high)
        model (str): ChatGPT model to use (gpt-4o, gpt-4o-mini, gpt-4)
    
    Returns:
        dict: Analysis results with scores, suggestions, and feedback
    """
    # Import performance monitoring
    try:
        from performance_monitor import AIAnalysisTimer
        MONITORING_AVAILABLE = True
    except ImportError:
        MONITORING_AVAILABLE = False
    
    # Check cache first if available
    if CACHE_AVAILABLE:
        # Generate cache key from parameters
        cache_key = generate_cache_key(essay_text, essay_type, f"{coaching_level}_{suggestion_aggressiveness}")
        cached_result = get_cached_analysis(cache_key)
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
    
    # Perform AI analysis
    logger.info(f"Performing new AI analysis for essay type: {essay_type}, coaching: {coaching_level}, aggressiveness: {suggestion_aggressiveness}")
    
    # Handle very long essays by chunking or truncating
    original_length = len(essay_text)
    if original_length > 8000:
        logger.warning(f"Essay is very long ({original_length} chars). Truncating to first 8000 characters for analysis.")
        essay_text = essay_text[:8000] + "...\n\n[Note: Essay was truncated for analysis due to length]"
    
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
    
    # Compose prompt with system message style for clarity and enhanced score explanations
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

4. ENHANCED SCORE EXPLANATIONS: For each score, provide detailed explanations that include:
   - Current strengths in this area
   - Specific areas for improvement
   - Examples from the essay
   - Actionable next steps
   
5. Provide 2-3 specific examples per rubric dimension that demonstrate both strengths and areas for growth

RUBRIC SCORING GUIDE:
- IDEAS (0-100): Content quality, thesis strength, argument development, evidence support
  90-100: Exceptional thesis, compelling evidence, sophisticated analysis
  80-89: Strong main ideas, good evidence, clear analysis
  70-79: Adequate ideas, some evidence, basic analysis
  60-69: Unclear ideas, weak evidence, superficial analysis
  Below 60: Poorly developed ideas, lacking evidence

- ORGANIZATION (0-100): Structure, flow, transitions, paragraph development
  90-100: Seamless flow, masterful transitions, perfect structure
  80-89: Clear organization, good transitions, logical flow
  70-79: Generally organized, adequate transitions
  60-69: Some organizational issues, unclear structure
  Below 60: Poor organization, confusing structure

- STYLE (0-100): Voice, word choice, sentence variety, engagement
  90-100: Distinctive voice, sophisticated vocabulary, varied syntax
  80-89: Clear voice, good word choice, some variety
  70-79: Adequate voice, appropriate vocabulary
  60-69: Weak voice, limited vocabulary, repetitive
  Below 60: No clear voice, poor word choice

- GRAMMAR (0-100): Mechanics, usage, conventions, clarity
  90-100: Error-free, sophisticated mechanics
  80-89: Few minor errors, strong mechanics
  70-79: Some errors, but doesn't impede understanding
  60-69: Several errors, occasionally confusing
  Below 60: Many errors, significantly impedes understanding

COACHING INTENSITY: {intensity}
SUGGESTION LEVEL: {aggressiveness_text}

Essay Type Focus: {essay_info['focus']}
Specific Checks: {', '.join(essay_info['specific_checks'])}

Return ONLY valid JSON with this enhanced structure:
{{
    "tagged_essay": "essay with inline tags",
    "scores": {{"ideas": 85, "organization": 80, "style": 75, "grammar": 90}},
    "score_reasons": {{
        "ideas": "STRENGTHS: Your thesis is clearly stated and arguable. You provide relevant evidence to support your main points. AREAS FOR IMPROVEMENT: Consider developing counterarguments to strengthen your position. Add more specific examples to support key claims. NEXT STEPS: Research 1-2 opposing viewpoints and address them in a dedicated paragraph.",
        "organization": "STRENGTHS: Your essay follows a logical structure with clear introduction and conclusion. Topic sentences guide each paragraph. AREAS FOR IMPROVEMENT: Transitions between paragraphs could be smoother. Some paragraphs contain multiple ideas that could be separated. NEXT STEPS: Add transitional phrases between paragraphs and consider splitting complex paragraphs.",
        "style": "STRENGTHS: Your writing voice is clear and appropriate for the audience. Word choice is generally effective. AREAS FOR IMPROVEMENT: Sentence structure could be more varied. Some word repetition throughout. NEXT STEPS: Practice varying sentence beginnings and length. Use a thesaurus to find synonyms for repeated words.",
        "grammar": "STRENGTHS: Strong command of basic grammar rules. Few mechanical errors that don't impede understanding. AREAS FOR IMPROVEMENT: Occasional subject-verb agreement issues. Some comma splices present. NEXT STEPS: Review comma rules and practice identifying complete vs. incomplete sentences."
    }},
    "suggestions": [
        {{"type": "replace", "text": "goodest -> best", "reason": "Use 'best' instead of 'goodest' - superlative form of 'good' is 'best', not 'goodest'"}}
    ],
    "examples": {{
        "ideas": ["Strong thesis clearly states position", "Evidence supports main argument", "Could benefit from addressing counterarguments"], 
        "organization": ["Clear introduction sets up essay well", "Good topic sentences", "Transitions between paragraphs need improvement"], 
        "style": ["Appropriate academic tone", "Clear voice throughout", "Could vary sentence structure more"], 
        "grammar": ["Correct verb tenses", "Proper punctuation in most cases", "Some subject-verb agreement issues"]
    }}
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
            model=model,  # Use the specified model parameter
            temperature=0.6,
            max_retries=3,
            essay_length=len(essay_text)
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
            # Ensure each suggestion has a detailed reason
            for i, suggestion in enumerate(analysis_data['suggestions']):
                if 'reason' not in suggestion or not suggestion['reason'].strip():
                    # Auto-generate detailed reason based on suggestion type
                    stype = suggestion.get('type', '').lower()
                    text = suggestion.get('text', '')
                    
                    if stype == 'delete':
                        suggestion['reason'] = f'Remove "{text}" - this word/phrase is unnecessary or grammatically incorrect and removing it improves clarity.'
                    elif stype == 'add':
                        suggestion['reason'] = f'Add "{text}" - this addition improves sentence structure, clarity, or grammatical correctness.'
                    elif stype == 'replace':
                        if '|' in text:
                            old, new = text.split('|', 1)
                            suggestion['reason'] = f'Replace "{old}" with "{new}" - this improves word choice, grammar, or style for better readability.'
                        else:
                            suggestion['reason'] = f'Replace this text - better word choice improves style and clarity.'
                    else:
                        suggestion['reason'] = f'Suggested change to improve writing quality and effectiveness.'
                
                # Ensure the reason is substantial (at least 20 characters)
                if len(suggestion['reason']) < 20:
                    suggestion['reason'] += ' This change enhances the overall quality of your writing.'
                
                logger.debug(f"Suggestion {i}: {suggestion.get('type')} - {suggestion.get('text')} - {suggestion['reason']}")

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
            cache_key = generate_cache_key(essay_text, essay_type, f"{coaching_level}_{suggestion_aggressiveness}")
            cache_analysis(cache_key, analysis_data)
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
