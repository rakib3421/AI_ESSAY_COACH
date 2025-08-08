# AI Essay Coach - Django Application

A comprehensive AI-powered essay analysis and feedback system built with Django. This application helps students improve their writing through intelligent analysis and provides teachers with tools to manage assignments and track student progress.

## 🚀 Features

### For Students
- **AI Essay Analysis**: Upload essays and receive instant AI-powered feedback
- **Multiple Essay Types**: Support for argumentative, narrative, expository, and more
- **Progress Tracking**: Monitor improvement over time with detailed analytics
- **Interactive Checklists**: Step-by-step improvement suggestions
- **File Upload & Text Paste**: Multiple ways to submit essays

### For Teachers
- **Assignment Management**: Create and manage essay assignments
- **Student Analytics**: Track individual and class-wide progress
- **Custom Feedback**: Add personalized feedback to AI analysis
- **Gradebook Integration**: Manage scores and submissions
- **Student-Teacher Assignment**: Organize student-teacher relationships

### Technical Features
- **AI Integration**: OpenAI GPT-powered essay analysis
- **Secure Authentication**: Role-based access control
- **File Processing**: Support for .docx and .txt files
- **Responsive Design**: Mobile-friendly interface
- **Database**: MySQL/MariaDB support
- **Admin Interface**: Django admin for system management

## 🛠 Installation & Setup

### Prerequisites
- Python 3.8+
- MySQL/MariaDB database
- Virtual environment (recommended)

### 1. Clone and Setup
```bash
# Clone the repository
git clone <repository-url>
cd AI_ESSAY_COACH

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration
Create a `.env` file in the project root:
```env
SECRET_KEY=your-secret-key-here
DEBUG=True

# Database Configuration
DB_HOST=localhost
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=essay_coach_db

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key
```

### 3. Database Setup
```bash
# Create database migrations
python manage.py makemigrations accounts
python manage.py makemigrations essays
python manage.py makemigrations assignments

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### 4. Static Files
```bash
# Collect static files for production
python manage.py collectstatic
```

### 5. Run Development Server
```bash
python manage.py runserver
```

The application will be available at `http://localhost:8000`

## 📁 Project Structure

```
AI_ESSAY_COACH/
├── essay_coach/              # Django project settings
│   ├── settings.py          # Main configuration
│   ├── urls.py              # URL routing
│   └── wsgi.py              # WSGI configuration
├── accounts/                 # User authentication app
│   ├── models.py            # User models
│   ├── views.py             # Authentication views
│   ├── forms.py             # User forms
│   └── urls.py              # Account URLs
├── essays/                   # Essay analysis app
│   ├── models.py            # Essay and analysis models
│   ├── views.py             # Essay views
│   ├── forms.py             # Essay forms
│   ├── ai_service.py        # AI integration
│   └── utils.py             # Utility functions
├── assignments/              # Assignment management app
│   ├── models.py            # Assignment models
│   ├── views.py             # Assignment views
│   ├── forms.py             # Assignment forms
│   └── urls.py              # Assignment URLs
├── analytics/                # Teacher analytics app
│   ├── views.py             # Analytics views
│   └── urls.py              # Analytics URLs
├── templates/                # HTML templates
│   ├── base.html            # Base template
│   ├── accounts/            # Account templates
│   ├── essays/              # Essay templates
│   ├── assignments/         # Assignment templates
│   └── analytics/           # Analytics templates
├── static/                   # Static files
│   ├── css/                 # Stylesheets
│   └── js/                  # JavaScript files
├── uploads/                  # File uploads
├── temp_data/                # Temporary storage
├── manage.py                 # Django management
└── requirements.txt          # Python dependencies
```

## 🔧 Configuration

### Django Settings
Key settings in `essay_coach/settings.py`:
- `DATABASES`: MySQL/MariaDB configuration
- `INSTALLED_APPS`: Django apps and third-party packages
- `MIDDLEWARE`: Security and session middleware
- `TEMPLATES`: Template configuration
- `STATIC_FILES`: Static file handling
- `AUTH_USER_MODEL`: Custom user model

### OpenAI Integration
Configure OpenAI settings in `.env`:
- `OPENAI_API_KEY`: Your OpenAI API key
- AI analysis settings in `essays/ai_service.py`

### File Upload Settings
- `MAX_CONTENT_LENGTH`: Maximum file size (16MB default)
- `ALLOWED_EXTENSIONS`: Supported file types (.docx, .txt)
- `MEDIA_ROOT`: File upload directory

## 🏃‍♂️ Usage

### For Students
1. **Sign Up**: Create a student account
2. **Upload Essay**: Submit essays via file upload or text paste
3. **View Analysis**: Review AI feedback and scores
4. **Track Progress**: Monitor improvement over time
5. **Complete Checklists**: Follow improvement suggestions

### For Teachers
1. **Create Account**: Sign up as a teacher
2. **Assign Students**: Manage student relationships
3. **Create Assignments**: Set up essay assignments
4. **Review Submissions**: Grade and provide feedback
5. **Analytics**: Track class progress and performance

### Admin Users
Access Django admin at `/admin/` to:
- Manage users and roles
- Monitor system usage
- Configure application settings
- View detailed analytics

## 🔒 Security Features

- **CSRF Protection**: Cross-site request forgery protection
- **XSS Prevention**: Input sanitization and validation
- **File Validation**: Secure file upload handling
- **Authentication**: Session-based user authentication
- **Authorization**: Role-based access control
- **SQL Injection Protection**: Django ORM prevents SQL injection

## 🚀 Production Deployment

### Environment Setup
```env
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
SECRET_KEY=production-secret-key
```

### Database Configuration
- Use production MySQL/PostgreSQL database
- Configure connection pooling
- Set up database backups

### Static Files
```bash
# Configure static file serving
STATIC_ROOT = '/path/to/static/files'
MEDIA_ROOT = '/path/to/media/files'

# Collect static files
python manage.py collectstatic --noinput
```

### Web Server
- Use Gunicorn or uWSGI for WSGI
- Configure Nginx for static files
- Set up SSL certificates

## 🧪 Testing

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test accounts
python manage.py test essays
python manage.py test assignments

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

## 📊 Monitoring & Analytics

### Built-in Analytics
- Student progress tracking
- Essay performance metrics
- Assignment completion rates
- Teacher dashboard analytics

### Logging
- Application logs in `app.log`
- Django debug toolbar (development)
- Error tracking and monitoring

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new features
5. Submit a pull request

## 📝 Migration from Flask

This Django application is a complete migration from the original Flask version. Key changes:

### Architecture Changes
- **Flask → Django**: Complete framework migration
- **Flask-SQLAlchemy → Django ORM**: Database layer migration
- **Flask Blueprints → Django Apps**: Modular structure
- **Jinja2 → Django Templates**: Template system migration

### New Features
- Django admin interface
- Enhanced user management
- Improved security features
- Better file handling
- Comprehensive testing framework

### Database Migration
The database schema remains compatible, but Django migrations handle:
- User model extension
- Foreign key relationships
- Index optimization
- Data integrity constraints

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Check MySQL service is running
   - Verify database credentials in `.env`
   - Ensure database exists

2. **OpenAI API Errors**
   - Verify API key is valid
   - Check API usage limits
   - Monitor rate limiting

3. **File Upload Issues**
   - Check file permissions on upload directory
   - Verify file size limits
   - Ensure supported file formats

4. **Static Files Not Loading**
   - Run `python manage.py collectstatic`
   - Check `STATIC_URL` and `STATIC_ROOT` settings
   - Verify web server configuration

### Debug Mode
Enable debug mode for development:
```env
DEBUG=True
```

## 📞 Support

For issues and questions:
- Check the troubleshooting section
- Review Django documentation
- Submit GitHub issues for bugs
- Contact development team for support

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Django framework and community
- OpenAI for AI capabilities
- Bootstrap for UI components
- Contributors and testers
