# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability within this project, please send an email to vn6295337@gmail.com. All security vulnerabilities will be promptly addressed.

Please do not publicly disclose the issue until it has been addressed by the team.

## Security Considerations

### API Keys and Secrets

- Never commit API keys, passwords, or other secrets to the repository
- Use environment variables or secure vaults for storing sensitive information
- The `.env.example` file shows which environment variables are required
- The `.gitignore` file excludes `.env` files from being committed

### Data Privacy

- The system processes documents locally before sending embeddings to Pinecone
- No raw document content is sent to LLM providers, only relevant chunks
- All processing respects data privacy regulations (GDPR, CCPA, etc.)

### Network Security

- API calls use HTTPS endpoints
- Timeout values are set for all external requests
- Error handling prevents leaking sensitive information

### Input Validation

- All user inputs are validated and sanitized
- File uploads are restricted to specific formats
- Size limits are enforced for document processing

## Best Practices

1. Regularly rotate API keys
2. Use the principle of least privilege for service accounts
3. Monitor API usage for unusual patterns
4. Keep dependencies up to date
5. Review and audit code changes for security implications

## Dependency Management

We regularly update dependencies to address known security vulnerabilities. Automated tools monitor our dependencies for security issues.

## Contact

For any security-related questions or concerns, please contact vn6295337@gmail.com.