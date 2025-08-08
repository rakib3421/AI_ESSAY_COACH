# 🎓 AI Essay Coach

A comprehensive web application that provides AI-powered essay analysis and revision assistance for students and teachers. This intelligent tutoring system helps improve writing skills through personalized feedback, interactive suggestions, and detailed performance analytics.

![AI Essay Coach](https://img.shields.io/badge/Version-2.0-blue)
![Python](https://img.shields.io/badge/Python-3.8+-green)
![Django](https://img.shields.io/badge/Django-5.2+-green)
![MySQL](https://img.shields.io/badge/MySQL-5.7+-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 🌟 Features

### 👨‍🎓 Student Portal
- **📝 Essay Upload & Analysis**: Upload .docx files for comprehensive AI-powered feedback
- **🔄 Interactive Suggestions**: View, accept, or reject AI suggestions with detailed explanations
- **📊 Progress Tracking**: Monitor improvement across multiple writing dimensions over time
- **📋 Assignment Management**: View and submit teacher-assigned essays with deadlines
- **💾 Export Functionality**: Download revised essays in proper Word format
- **🎯 Personalized Dashboard**: Track scores, feedback history, and writing goals

### 👩‍🏫 Teacher Portal
- **👥 Student Management**: Comprehensive view of all student submissions and progress
- **✍️ Assignment Creation**: Create and manage essay assignments with custom rubrics
- **💭 Feedback System**: Provide additional personalized feedback on student work
- **📈 Analytics Dashboard**: Track class-wide performance trends and insights
- **✅ Customizable Checklists**: Configure revision guidelines by essay type
- **📊 Performance Reports**: Generate detailed reports on student progress

### 🤖 AI Analysis Features
- **🔍 Essay Type Classification**: Argumentative, Narrative, Literary Analysis, Expository, Comparative, Hybrid
- **📝 Granular Feedback**: Word choice, sentence structure, flow, and coherence suggestions
- **📊 Comprehensive Scoring**: Ideas (30%), Organization (25%), Style (20%), Grammar (25%)
- **🎨 Visual Suggestions**: Blue strikethrough for deletions, red underline for additions
- **💡 Intelligent Explanations**: Detailed reasoning behind each suggestion
- **🔄 Iterative Improvement**: Multiple revision rounds with progress tracking

## 🛠️ Technology Stack

### Backend
- **🐍 Python Django**: Robust web framework with modular app architecture
- **🗄️ MySQL**: Relational database with connection pooling
- **🤖 OpenAI GPT-4**: Advanced AI model for essay analysis
- **🔐 Security**: Werkzeug password hashing, session management

### Frontend
- **🌐 HTML5 & CSS3**: Modern responsive design
- **🎨 Bootstrap 5**: Professional UI components
- **⚡ JavaScript**: Interactive user experience
- **📱 Responsive Design**: Mobile-friendly interface

### Infrastructure
- **📄 Document Processing**: python-docx for Word file handling
- **🔧 Configuration Management**: python-dotenv for environment variables
- **📊 Monitoring**: Custom performance tracking and error handling
- **🚀 Connection Pooling**: Optimized database performance

## 🚀 Installation

### Prerequisites

- Python 3.8+
- MySQL 5.7+
- OpenAI API key
- Modern web browser

### Quick Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/rakib3421/AI_ESSAY_COACH.git
   cd AI_ESSAY_COACH
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

   Create a `.env` file in the root directory:

   ```env
   # Database Configuration
   DB_HOST=localhost
   DB_USER=your_mysql_user
   DB_PASSWORD=your_mysql_password
   DB_NAME=essay_revision

   # OpenAI API
   OPENAI_API_KEY=your_openai_api_key

   # Django Configuration
   SECRET_KEY=your_django_secret_key
   
   # Optional: Performance Settings
   DB_POOL_ENABLED=true
   CACHE_ENABLED=true
   ```

5. **Setup database**

   ```bash
   python manage.py migrate
   ```

6. **Run the application**

   ```bash
   python manage.py runserver
   ```

7. **Access the application**

   Open your browser to `http://localhost:8000`

## 📚 Usage

### For Students

1. **🔐 Account Setup**: Create an account with role "Student"
2. **📤 Upload Essay**: Use the upload form to submit .docx files (up to 16MB)
3. **🔍 Review Feedback**: View AI suggestions with detailed explanations
4. **✅ Interactive Editing**: Click on highlighted text to accept/reject suggestions
5. **📈 Track Progress**: Monitor scores and improvement over time
6. **💾 Export Essays**: Download revised versions in Word format
7. **📋 Assignment Submission**: Complete teacher-assigned essays

### For Teachers

1. **🔐 Account Setup**: Create an account with role "Teacher"
2. **✍️ Create Assignments**: Set up essay prompts with custom guidelines
3. **👀 Review Submissions**: View student essays and AI feedback
4. **💬 Provide Feedback**: Add personal comments and guidance
5. **📊 Monitor Progress**: Track individual and class performance
6. **👥 Manage Students**: View submission history and analytics
7. **📈 Generate Reports**: Create performance reports for parents/administration

## 🔌 API Reference

### Essay Management

- `POST /student/upload` - Upload essay for AI analysis
- `GET /student/essay/<id>` - View essay with suggestions
- `GET /export/<id>` - Export essay as .docx file
- `GET /student/essays` - List all user essays
- `GET /student/progress` - Get progress analytics

### Suggestion Management

- `GET /api/essay/<id>/suggestions` - Get AI suggestions for essay
- `POST /api/suggestion/<id>/accept` - Accept specific suggestion
- `POST /api/suggestion/<id>/reject` - Reject specific suggestion
- `GET /api/suggestion/<id>/explanation` - Get detailed explanation

### Teacher Functions

- `POST /teacher/create_assignment` - Create new assignment
- `POST /teacher/feedback/<id>` - Provide teacher feedback
- `GET /teacher/students` - Get all assigned students
- `GET /teacher/analytics` - Get class analytics
- `PUT /teacher/assignment/<id>` - Update assignment details

### Authentication

- `POST /login` - User authentication
- `POST /signup` - User registration
- `POST /logout` - User logout
- `GET /profile` - Get user profile

## 🗄️ Database Schema

### Core Tables

- **`users`**: User accounts, roles, and authentication
- **`essays`**: Essay content, metadata, and scoring
- **`assignments`**: Teacher-created essay assignments
- **`essay_suggestions`**: AI-generated improvement suggestions
- **`assignment_submissions`**: Student assignment submissions
- **`student_teacher_assignments`**: Student-teacher relationships
- **`performance_analytics`**: Historical performance data
- **`system_logs`**: Application monitoring and error tracking

### Entity Relationships

```sql
users (1) -----> (M) essays
users (1) -----> (M) assignments [teachers only]
assignments (1) -> (M) assignment_submissions
essays (1) -----> (M) essay_suggestions
users (1) -----> (M) student_teacher_assignments
```

## 🤖 AI Integration

The application leverages OpenAI's GPT-4 model for sophisticated essay analysis:

**Core Functions:**

- **Content Analysis**: Deep understanding of essay structure and arguments
- **Type Classification**: Automatic detection of essay types and genres
- **Suggestion Generation**: Specific, actionable improvement recommendations
- **Rubric Scoring**: Comprehensive evaluation across multiple dimensions
- **Explanatory Feedback**: Detailed reasoning behind each suggestion

### Supported Essay Types

1. **📝 Argumentative**: Thesis development, evidence analysis, counterarguments, source integration
2. **📖 Narrative**: Dialogue enhancement, imagery, narrative arc, pacing improvements
3. **🔍 Literary Analysis**: Citation formatting, present tense consistency, analytical depth
4. **📊 Expository**: Clarity, organization, factual accuracy, logical flow
5. **⚖️ Comparative**: Balance, contrast development, synthesis of ideas
6. **🔄 Hybrid**: Multi-genre analysis with adaptive feedback strategies

## 📊 Scoring System

Essays are evaluated on a **100-point scale** across four key dimensions:

- **💡 Ideas (30 points)**: Content quality, originality, and development
- **🏗️ Organization (25 points)**: Structure, flow, and logical progression
- **✨ Style (20 points)**: Voice, word choice, and sentence variety
- **📝 Grammar (25 points)**: Mechanics, conventions, and clarity

### Performance Levels

- **🏆 Exemplary (90-100)**: Publication-ready writing
- **✅ Proficient (80-89)**: Strong academic writing
- **📈 Developing (70-79)**: Good foundation, needs refinement
- **🔧 Beginning (60-69)**: Requires significant improvement
- **⚠️ Needs Support (<60)**: Fundamental skills development needed

## 🔒 Security Features

- **🔐 Password Security**: Django's built-in password hashing with salt
- **🛡️ Session Management**: Secure Django session handling
- **👤 Role-Based Access**: Student/Teacher permission system
- **🧹 Input Validation**: Comprehensive data sanitization
- **💉 SQL Injection Prevention**: Django ORM with parameterized queries
- **📁 File Security**: Safe file upload and processing
- **🔍 XSS Protection**: Cross-site scripting prevention

## 📁 Project Structure

```
AI_ESSAY_COACH/
├── 📄 manage.py             # Django management script
├── 🔧 essay_coach/          # Django project settings
│   ├── settings.py          # Configuration management
│   ├── urls.py              # URL routing
│   └── wsgi.py              # WSGI configuration
├── �️ essays/               # Essays Django app
├── � accounts/             # User authentication app
├── � assignments/          # Assignments app
├── � analytics/            # Analytics app
├── 📊 monitoring.py         # Performance monitoring
├── 🔗 db_pool.py            # Database connection pooling
├── 📦 requirements.txt      # Python dependencies
├── 🌱 setup_database.py     # Database initialization
├── 📚 README.md             # This file
├── 🎨 templates/            # HTML templates
│   ├── 🏠 base.html
│   ├── 🏛️ index.html
│   ├── 🔑 login.html
│   ├── ✍️ signup.html
│   ├── 👨‍🎓 student/          # Student interface
│   │   ├── 📊 dashboard.html
│   │   ├── 📤 upload.html
│   │   ├── 📝 essays.html
│   │   ├── 👁️ view_essay.html
│   │   ├── 💬 feedback.html
│   │   └── 📈 progress.html
│   └── 👩‍🏫 teacher/          # Teacher interface
│       ├── 📊 dashboard.html
│       ├── 👥 students.html
│       ├── ✍️ create_assignment.html
│       ├── 📋 submissions.html
│       └── 📈 analytics.html
├── 🎨 static/               # Static assets
│   ├── 🎨 css/
│   │   └── style.css
│   └── ⚡ js/
│       └── app.js
├── 📤 uploads/              # Temporary file storage
├── 💾 temp_data/            # Temporary data processing
└── 🗂️ __pycache__/          # Python cache files
```

## 🤝 Contributing

We welcome contributions from the community! Here's how you can help:

### Getting Started

1. **🍴 Fork the repository**
2. **🌿 Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **💻 Make your changes** with clear, commented code
4. **✅ Add tests** if applicable
5. **📝 Update documentation** as needed
6. **🔍 Test thoroughly** in both student and teacher modes
7. **📤 Submit a pull request** with detailed description

### Development Guidelines

- **🐍 Code Style**: Follow PEP 8 for Python code
- **📝 Documentation**: Comment complex functions and classes
- **🧪 Testing**: Include unit tests for new features
- **🔒 Security**: Follow secure coding practices
- **📊 Performance**: Consider performance implications
- **♿ Accessibility**: Ensure UI accessibility standards

### Areas for Contribution

- **🌍 Internationalization**: Multi-language support
- **📱 Mobile**: Enhanced mobile interface
- **🔌 Integrations**: LMS platform connections
- **🎨 UI/UX**: Interface improvements
- **🧪 Testing**: Automated test coverage
- **📈 Analytics**: Advanced reporting features

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

```text
MIT License

Copyright (c) 2025 AI Essay Coach

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

## 📞 Support & Contact

### Getting Help

- **📚 Documentation**: Check this README and code comments
- **🐛 Bug Reports**: Create an issue with detailed reproduction steps
- **💡 Feature Requests**: Submit enhancement proposals via issues
- **❓ Questions**: Use GitHub Discussions for general questions

### Contact Information

- **👨‍💻 Developer**: [Rakib](https://github.com/rakib3421)
- **📧 Email**: Support available through GitHub issues
- **🐙 Repository**: [AI_ESSAY_COACH](https://github.com/rakib3421/AI_ESSAY_COACH)

## 🔮 Future Enhancements

### Planned Features

- **📄 Multi-Format Support**: PDF, TXT, Google Docs integration
- **📊 Advanced Analytics**: Detailed writing pattern analysis
- **🤝 Real-time Collaboration**: Live editing and sharing
- **📱 Mobile Application**: Native iOS and Android apps
- **🔗 LMS Integration**: Canvas, Blackboard, Google Classroom
- **🌍 Multi-language Support**: International language analysis
- **🔍 Plagiarism Detection**: Academic integrity checking
- **🎤 Voice Input**: Speech-to-text essay composition
- **🤖 Advanced AI Models**: Integration with latest language models
- **📈 Predictive Analytics**: Learning outcome predictions

### Research Opportunities

- **🧠 Learning Patterns**: Analysis of writing improvement trajectories
- **📊 Effectiveness Studies**: Measurement of educational impact
- **🎯 Personalization**: Adaptive feedback based on individual needs
- **🔄 Iterative Learning**: Multi-round revision optimization

## 🐛 Troubleshooting

### Common Issues

1. **🔌 Database Connection Errors**
   - Verify MySQL is running and accessible
   - Check database credentials in `.env` file
   - Ensure database `essay_revision` exists
   - Test connection with: `mysql -u username -p -h localhost`

2. **🤖 OpenAI API Issues**
   - Verify API key is valid and active
   - Check API quota and billing status
   - Monitor rate limits and retry logic
   - Test with: `curl -H "Authorization: Bearer YOUR_KEY" https://api.openai.com/v1/models`

3. **📁 File Upload Problems**
   - Check `uploads/` directory permissions
   - Verify file size under 16MB limit
   - Ensure `.docx` format compliance
   - Clear browser cache if needed

4. **⚡ Performance Issues**
   - Enable database connection pooling
   - Monitor system resource usage
   - Check network connectivity to OpenAI
   - Review application logs for bottlenecks

5. **🔐 Authentication Problems**
   - Clear browser cookies and sessions
   - Verify SECRET_KEY in environment
   - Check user role assignments in database
   - Reset password if needed

### Debug Mode

Enable debug mode for development:

```python
# In app.py
if __name__ == '__main__':
    app.run(host='localhost', port=5000, debug=True)
```

### Error Logs

Monitor application logs for detailed error information:

```bash
# Check application logs
tail -f app.log

# Check MySQL error logs
sudo tail -f /var/log/mysql/error.log
```

---

## 🎯 Quick Start Checklist

- [ ] Python 3.8+ installed
- [ ] MySQL server running
- [ ] OpenAI API key obtained
- [ ] Repository cloned
- [ ] Virtual environment created
- [ ] Dependencies installed
- [ ] Environment variables configured
- [ ] Database initialized
- [ ] Application running
- [ ] First user account created
- [ ] Sample essay uploaded
- [ ] AI feedback received

---

**🎓 AI Essay Coach** - Empowering students and teachers through intelligent writing assistance.

Built with care for educational excellence.
