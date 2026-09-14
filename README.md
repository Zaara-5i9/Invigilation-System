# Invigilation Management System

A comprehensive Django-based web application for managing exam invigilation duties in educational institutions.

## 🚀 Features

### For Administrators
- **Faculty Management**: Create and manage faculty profiles with batch operations
- **Exam Management**: Schedule exams with automated course selection
- **Smart Allocation**: Intelligent faculty assignment with bias prevention
- **Comprehensive Reports**: Analytics dashboard with workload distribution
- **Timetable Management**: Admin interface to manage any faculty's timetable
- **Notification System**: Automated reminders and status updates

### For Faculty
- **Personal Dashboard**: View assignments and notifications
- **Interactive Timetable**: Grid-based timetable management
- **Leave Management**: Apply for and track leave requests
- **Assignment Response**: Accept or decline invigilation duties
- **Workload Visibility**: View personal workload statistics

## 🏗️ System Architecture

### Core Applications
- **accounts**: User management and authentication
- **exams**: Exam scheduling and invigilation management
- **timetable**: Faculty timetable management
- **leaves**: Leave application and approval system
- **notifications**: Real-time notification system
- **logs**: Comprehensive audit logging

### Key Features
- **Cross-Department Allocation**: Prevents bias by avoiding same-department assignments
- **Smart Scheduling**: Considers faculty availability and teaching schedules
- **Automated Workflows**: Email notifications and reminder systems
- **Comprehensive Logging**: Full audit trail for all actions
- **Responsive Design**: Works on desktop, tablet, and mobile devices

## 🛠️ Technology Stack

- **Backend**: Django 4.2.23, Python 3.x
- **Database**: SQLite (development), PostgreSQL (production ready)
- **Frontend**: Bootstrap 5, JavaScript, Chart.js
- **Email**: Django email backend with SMTP support
- **Authentication**: Django's built-in auth with OTP verification

## 📋 Quick Start

### Prerequisites
- Python 3.8+
- pip (Python package manager)
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd invigilation-system
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Start development server**
   ```bash
   python manage.py runserver
   ```

8. **Access the application**
   - Open http://127.0.0.1:8000 in your browser
   - Login with your superuser credentials

## 📖 Documentation

Comprehensive documentation is available in the `docs/` folder:

- **[Quick Reference Card](docs/QUICK_REFERENCE_CARD.md)** - Essential commands and URLs
- **[Setup Guide](docs/SETUP_GUIDE.md)** - Detailed installation instructions
- **[System Architecture](docs/SYSTEM_ARCHITECTURE.md)** - Technical overview
- **[Complete Implementation Summary](docs/COMPLETE_IMPLEMENTATION_SUMMARY.md)** - Full feature list

## 🔧 Configuration

### Environment Variables (.env)
```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

### Key Settings
- **Time Zones**: Configured for Indian Standard Time (IST)
- **Email Backend**: SMTP with Gmail support
- **Static Files**: Configured for development and production
- **Database**: SQLite for development, easily configurable for PostgreSQL

## 🎯 Key Workflows

### Exam Allocation Process
1. **Create Exams**: Batch creation with department/year/semester selection
2. **Smart Assignment**: System suggests optimal faculty allocation
3. **Bias Prevention**: Prioritizes cross-department faculty assignment
4. **Notification**: Automated emails to assigned faculty
5. **Response Tracking**: Faculty can accept/decline with reasons
6. **Analytics**: Comprehensive reports on allocation success

### Faculty Management
1. **Batch Creation**: Create multiple faculty profiles simultaneously
2. **Credential Distribution**: Automated email with login credentials
3. **First Login Flow**: OTP verification and password change
4. **Timetable Management**: Both self-service and admin interfaces
5. **Leave Integration**: Leave status affects availability for duties

## 📊 Analytics & Reports

- **Summary Dashboard**: Key metrics and trends
- **Faculty Workload**: Individual and comparative analysis
- **Department Statistics**: Cross-department performance
- **Allocation Success**: Bias prevention effectiveness
- **Response Rates**: Faculty engagement metrics

## 🔐 Security Features

- **OTP Verification**: Two-factor authentication for first login
- **Password Policies**: Enforced password changes
- **Audit Logging**: Complete action history with IP tracking
- **Role-Based Access**: Separate admin and faculty interfaces
- **CSRF Protection**: Built-in Django security features

## 🚀 Production Deployment

### Checklist
- [ ] Set `DEBUG=False` in production
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Use PostgreSQL database
- [ ] Set up SSL certificate
- [ ] Configure email with app passwords
- [ ] Set up automated backups
- [ ] Configure web server (nginx/Apache)
- [ ] Set up process manager (gunicorn/uwsgi)

### Recommended Stack
- **Web Server**: Nginx
- **WSGI Server**: Gunicorn
- **Database**: PostgreSQL
- **Caching**: Redis (optional)
- **Monitoring**: Django logging + external monitoring

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:
1. Check the documentation in `docs/`
2. Review the troubleshooting section in the Quick Reference Card
3. Open an issue on GitHub
4. Contact the development team

## 🎓 Educational Context

This system is designed for B.Tech colleges with:
- **4-year program structure**
- **Multiple departments** (CSE, ECE, EEE, MECH, CIVIL, etc.)
- **Semester-based courses**
- **Regular examination schedules**
- **Faculty workload management needs**

---

**Version**: 1.0  
**Status**: Production Ready ✅  
**Last Updated**: March 2026