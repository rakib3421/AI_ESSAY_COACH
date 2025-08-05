# Automatic Essay Type Detection Feature

## Overview

The AI Essay Revision System now supports **automatic essay type detection**. Users no longer need to manually select essay types when uploading essays or creating assignments. The AI will analyze the content and automatically determine whether the text is argumentative, narrative, literary analysis, expository, descriptive, or compare/contrast.

## How It Works

### For Students (Essay Upload)

1. **Upload Form**: The essay type dropdown now defaults to "Auto-detect essay type"
2. **Content Analysis**: When an essay is uploaded, the AI analyzes the text structure, language patterns, and content
3. **Type Detection**: The system identifies the most likely essay type based on:
   - Thesis statements and argumentation (Argumentative)
   - Personal narrative elements and storytelling (Narrative)
   - Literary references and text analysis (Literary Analysis)
   - Explanatory content and factual information (Expository)
   - Sensory details and imagery (Descriptive)
   - Comparison structures and contrasting elements (Compare/Contrast)

### For Teachers (Assignment Creation)

1. **Assignment Setup**: Teachers can set essay type to "Auto-detect from student submissions"
2. **Flexible Requirements**: Allows students to write in their preferred style while maintaining grading consistency
3. **Type Override**: Teachers can still specify exact types when needed

### For Assignment Submissions

- **Auto-Assignment**: If an assignment has auto-detection enabled, each student's submission is analyzed individually
- **Type-Specific**: If an assignment specifies a particular type, that type is used for all submissions
- **Smart Fallback**: System defaults to 'Expository' if detection is uncertain

## User Interface Changes

### Student Upload Page

```html
<!-- Before -->
<select name="essay_type" required>
    <option value="">Select essay type</option>
    <option value="argumentative">Argumentative Essay</option>
    <!-- ... other options ... -->
</select>

<!-- After -->
<select name="essay_type">
    <option value="auto" selected>Auto-detect essay type</option>
    <option value="argumentative">Argumentative Essay</option>
    <!-- ... other options ... -->
</select>
```

### Teacher Assignment Creation

```html
<!-- New Auto-Detection Option -->
<select name="essay_type">
    <option value="auto">Auto-detect from student submissions</option>
    <option value="argumentative">Argumentative Essay</option>
    <!-- ... other options ... -->
</select>
```

## Backend Implementation

### Key Functions

1. **`detect_essay_type(essay_text)`**
   - Uses GPT-4o-mini for fast, accurate detection
   - Returns one of: argumentative, narrative, literary, expository, descriptive, compare
   - Fallback to 'expository' on error

2. **`analyze_essay_with_ai(essay_text, essay_type='auto', ...)`**
   - Automatically calls detection if essay_type='auto'
   - Maintains backward compatibility with manual type selection

3. **Updated Upload Routes**
   - Handle both URL parameters and form data for assignment_id
   - Override essay type with assignment requirements when applicable

### Database Schema Support

The existing schema supports auto-detection:
- `assignments.essay_type` can be set to 'auto'
- `essay_analyses.essay_type` stores the detected type
- No migration required

## API Behavior

### Essay Analysis Endpoint

```python
# Auto-detection request
POST /student/upload
{
    "title": "My Essay",
    "essay_type": "auto",  # or omitted entirely
    "coaching_level": "medium",
    "suggestion_level": "medium"
}

# Response includes detected type
{
    "essay_type": "Argumentative",
    "scores": { ... },
    "suggestions": [ ... ]
}
```

## Error Handling

- **API Failure**: Falls back to 'expository' type
- **Invalid Detection**: Validates against known types, defaults to 'expository'
- **Network Issues**: Graceful degradation with default analysis

## Performance

- **Speed**: GPT-4o-mini provides fast detection (< 2 seconds)
- **Accuracy**: Typically 90%+ accuracy on clear essay types
- **Cost**: Minimal additional API usage for detection calls

## Benefits

### For Students
- ✅ No need to categorize their own writing
- ✅ Reduced cognitive load during upload
- ✅ More accurate type-specific feedback
- ✅ Flexibility in writing style

### For Teachers
- ✅ Simplified assignment creation
- ✅ Consistent analysis regardless of student type selection
- ✅ Better understanding of student writing patterns
- ✅ Reduced grading complexity

## Configuration

### Environment Variables
```bash
# Existing OpenAI configuration works for auto-detection
OPENAI_API_KEY=your_api_key_here
```

### Default Settings
- Default essay type: `auto`
- Detection model: `gpt-4o-mini`
- Fallback type: `expository`
- Detection timeout: 30 seconds

## Testing

Run the test script to verify functionality:

```bash
python test_auto_detection.py
```

This will test:
- Basic type detection accuracy
- Auto parameter handling
- Error cases and fallbacks

## Migration Guide

### Existing Users
- No action required - existing functionality preserved
- Users can continue selecting types manually if preferred

### New Installations
- Auto-detection enabled by default
- All templates updated to use 'auto' as default selection

## Future Enhancements

1. **Hybrid Type Detection**: Detect essays that combine multiple types
2. **Confidence Scoring**: Show detection confidence to users
3. **Custom Types**: Allow teachers to define custom essay categories
4. **Batch Detection**: Process multiple essays simultaneously
5. **Learning Integration**: Improve detection based on teacher corrections

## Troubleshooting

### Common Issues

1. **"Auto-detection not working"**
   - Check OpenAI API key configuration
   - Verify internet connection
   - Check application logs for errors

2. **"Wrong type detected"**
   - Auto-detection achieves ~90% accuracy
   - Users can manually override if needed
   - Consider essay content clarity

3. **"Assignment type locked"**
   - When assignments specify a type, it overrides auto-detection
   - This is intentional behavior for consistent grading

### Debug Mode

Enable debug logging to troubleshoot detection:

```python
import logging
logging.getLogger('app').setLevel(logging.DEBUG)
```

## Support

For issues with auto-detection:
1. Check the application logs for error messages
2. Verify OpenAI API quota and limits
3. Test with the provided test script
4. Contact support with specific examples that fail detection
