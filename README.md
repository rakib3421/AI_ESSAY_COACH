# AI Essay Revision Application

A comprehensive web application that provides AI-powered essay analysis and revision assistance for students and teachers. Built with Flask, MySQL, and OpenAI API integration.

## Features

### Student Portal
- **Essay Upload & Analysis**: Upload .docx files for AI-powered feedback
- **Interactive Suggestions**: View, accept, or reject AI suggestions with explanations
- **Progress Tracking**: Monitor improvement across multiple writing dimensions
- **Assignment Management**: View and submit teacher-assigned essays
- **Export Functionality**: Download revised essays in proper format

### Teacher Portal
- **Student Management**: View all student submissions and progress
- **Assignment Creation**: Create and manage essay assignments
- **Feedback System**: Provide additional feedback on student work
- **Analytics Dashboard**: Track class-wide performance and trends
- **Customizable Checklists**: Configure revision guidelines by essay type

### AI Analysis Features
- **Essay Type Classification**: Argumentative, Narrative, Literary Analysis, Hybrid
- **Granular Feedback**: Word choice, sentence structure, flow suggestions
- **Scoring System**: Ideas (30%), Organization (25%), Style (20%), Grammar (25%)
- **Suggestion Formatting**: Blue strikethrough for deletions, red underline for additions

## Technology Stack

- **Backend**: Python Flask
- **Database**: MySQL with PyMySQL
- **AI**: OpenAI GPT-3.5-turbo API
- **Frontend**: HTML5, CSS3, Bootstrap 5, JavaScript
- **Document Processing**: python-docx
- **Authentication**: Flask sessions with password hashing

## Installation

### Prerequisites
- Python 3.8+
- MySQL 5.7+
- OpenAI API key

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ESSAY
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   - Copy `.env` file and update with your settings:
   ```env
   DB_HOST=localhost
   DB_USER=your_mysql_user
   DB_PASSWORD=your_mysql_password
   DB_NAME=essay_revision
   OPENAI_API_KEY=your_openai_api_key
   SECRET_KEY=your_flask_secret_key
   ```

5. **Setup database**
   ```bash
   python setup_database.py
   ```

6. **Run the application**
   ```bash
   python app.py
   ```

7. **Access the application**
   - Open your browser to `http://localhost:5000`

## Usage

### For Students

1. **Sign Up**: Create an account with role "Student"
2. **Upload Essay**: Use the upload form to submit .docx files
3. **Review Feedback**: View AI suggestions and explanations
4. **Accept/Reject Suggestions**: Click on highlighted text to interact
5. **Track Progress**: Monitor scores and improvement over time
6. **Export Essays**: Download revised versions in Word format

### For Teachers

1. **Sign Up**: Create an account with role "Teacher"
2. **Create Assignments**: Set up essay prompts with guidelines
3. **Review Submissions**: View student essays and AI feedback
4. **Provide Feedback**: Add personal comments and guidance
5. **Monitor Progress**: Track individual and class performance
6. **Manage Students**: View submission history and analytics

## API Endpoints

### Essay Management
- `POST /student/upload` - Upload essay for analysis
- `GET /student/essay/<id>` - View essay with suggestions
- `GET /export/<id>` - Export essay as .docx file

### Suggestions
- `GET /api/essay/<id>/suggestions` - Get AI suggestions
- `POST /api/suggestion/<id>/accept` - Accept suggestion
- `POST /api/suggestion/<id>/reject` - Reject suggestion

### Teacher Functions
- `POST /teacher/create_assignment` - Create new assignment
- `POST /teacher/feedback/<id>` - Provide teacher feedback

## Database Schema

### Core Tables
- `users`: User accounts and roles
- `essays`: Essay content and scores
- `assignments`: Teacher-created assignments
- `essay_suggestions`: AI-generated suggestions
- `assignment_submissions`: Student assignment submissions
- `student_teacher_assignments`: Student-teacher relationships

## AI Integration

The application uses OpenAI's GPT-4o-mini model to:
- Analyze essay content based on type
- Generate specific improvement suggestions
- Provide explanations for recommendations
- Calculate rubric-based scores

### Essay Types Supported
1. **Argumentative**: Thesis, evidence, counterarguments, sources
2. **Narrative**: Dialogue, imagery, narrative arc, pacing
3. **Literary Analysis**: Citations, present tense, analytical depth
4. **Hybrid**: Combined analysis for mixed-type essays

## Scoring Rubric

Essays are scored on a 100-point scale:
- **Ideas (30 points)**: Content quality and development
- **Organization (25 points)**: Structure and flow
- **Style (20 points)**: Voice and word choice
- **Grammar (25 points)**: Mechanics and conventions

## Security Features

- Password hashing with Werkzeug
- Session-based authentication
- Role-based access control
- Input validation and sanitization
- SQL injection prevention

## File Structure

```
ESSAY/
├── app.py                 # Main Flask application
├── setup_database.py     # Database initialization
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables
├── templates/            # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── signup.html
│   ├── student/          # Student templates
│   └── teacher/          # Teacher templates
├── static/               # Static assets
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
└── uploads/              # Temporary file storage
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support and questions:
- Check the documentation
- Review the code comments
- Create an issue in the repository

## Future Enhancements

- PDF and TXT file support
- Advanced analytics dashboard
- Real-time collaboration
- Mobile application
- Integration with LMS platforms
- Multiple language support
- Plagiarism detection
- Voice-to-text essay input

## Troubleshooting

### Common Issues

1. **Database Connection**: Ensure MySQL is running and credentials are correct
2. **OpenAI API**: Verify API key is valid and has sufficient credits
3. **File Upload**: Check file permissions and upload directory
4. **Dependencies**: Use exact versions from requirements.txt

### Error Logs
Check the Flask console output for detailed error messages and stack traces.

---

**Note**: This application is designed for educational purposes and requires proper OpenAI API usage compliance.
