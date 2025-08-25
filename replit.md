# CV Optimizer Pro

## Overview

cv Pro is a Progressive Web Application (PWA) that uses artificial intelligence to optimize resumes and cover letters for specific job positions. The application allows users to upload PDF CVs, input job descriptions, and receive AI-powered optimizations to improve their chances in the recruitment process. It features a freemium model with basic free functionality and premium paid features.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Template Engine**: Jinja2 templates with Flask for server-side rendering
- **UI Framework**: Bootstrap 5 with dark theme and glassmorphism design
- **Progressive Web App**: Full PWA implementation with service worker, manifest.json, and offline capabilities
- **Client-side Logic**: Vanilla JavaScript for form handling, file uploads, and user interactions
- **Responsive Design**: Mobile-first approach with PWA meta tags and app-like experience

### Backend Architecture
- **Web Framework**: Flask with SQLAlchemy ORM for database operations
- **Application Structure**: Modular design with separate utilities for PDF processing and AI integration
- **Session Management**: Flask sessions with in-memory storage for CV processing sessions
- **File Handling**: Secure file upload system with validation for PDF files (16MB limit)
- **Database Models**: SQLAlchemy models for CV uploads and analysis results with timestamp tracking

### Data Storage Solutions
- **Primary Database**: PostgreSQL for production with SQLite fallback for development
- **Session Storage**: Server-side session management for CV processing workflow
- **File Storage**: Local filesystem storage for uploaded PDF files in secure uploads directory
- **Database Schema**: Relational design with CV uploads, analysis results, and user tracking

### Authentication and Authorization
- **Session-based Authentication**: Flask session management without persistent user accounts in current implementation
- **File Security**: Secure filename handling using Werkzeug utilities
- **API Key Management**: Environment variable configuration for external service credentials

### External Service Integrations
- **AI Processing**: OpenRouter API integration for CV optimization using Qwen model
- **PDF Processing**: PyPDF2 library for text extraction from uploaded documents
- **Payment Processing**: Stripe integration configured for Polish market (PLN pricing)
- **Development Environment**: Replit-specific configurations and deployment settings

## External Dependencies

### Third-party APIs
- **OpenRouter API**: AI/LLM service for CV optimization and analysis using Qwen-2.5-72B model
- **Stripe API**: Payment processing for premium features (9.99 PLN single use, 29.99 PLN monthly)

### External Libraries and Services
- **PyPDF2**: PDF text extraction and processing
- **Flask ecosystem**: Flask-SQLAlchemy, Werkzeug for web framework functionality
- **Bootstrap 5**: Frontend UI framework with Replit dark theme
- **Bootstrap Icons**: Icon library for user interface elements

### Development and Deployment
- **Environment Management**: python-dotenv for configuration management
- **WSGI Server**: Gunicorn for production deployment
- **Database Drivers**: PostgreSQL adapter with SQLite fallback support
- **CDN Resources**: Bootstrap CSS/JS, Bootstrap Icons served from CDN

### Database Configuration
- **PostgreSQL**: Primary database with connection pooling and health checks
- **SQLite**: Development fallback database stored locally
- **Connection Management**: Pool recycling and pre-ping health checks configured