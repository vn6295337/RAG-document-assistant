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

### Zero-Disk Architecture

The system implements a **zero-disk-touch** architecture for document processing:

#### What This Means

| Data State | Storage Location | Persistence |
|------------|------------------|-------------|
| File bytes during parsing | RAM only | Request duration (~1-5s) |
| Parsed document structure | RAM only | Request duration |
| Generated embeddings | Pinecone | Persistent (irreversible) |
| Original text | Never stored | N/A |

#### Implementation Details

- **Docling Processing**: Uses `DocumentStream` with `BytesIO` for in-memory parsing
- **Fallback Parsing**: PyPDF2 (PDFs) or raw decode (TXT/MD) when Docling unavailable
- **No Temp Files**: Files are never written to `/tmp/` or any disk location
- **Automatic Purge**: Memory released when HTTP request completes
- **Audit Logging**: Processing logs include "Zero-disk processing" markers

#### Parsing Fallback Chain

```
1. Docling (BytesIO) ──► Success: High-quality structured output
         │
         ▼ Fails
2. PyPDF2/Raw text ───► Success: Basic text extraction
         │
         ▼ Fails
3. Return error ──────► "No text extracted" (e.g., scanned PDFs)
```

All fallback methods maintain zero-disk guarantees (in-memory processing only).

#### Deployment Requirements for Zero-Disk Guarantee

To guarantee zero-disk-touch, the deployment environment must meet:

1. **Swap Disabled**: OS swap/page file must be disabled
   ```bash
   # Verify swap is disabled
   swapon --show  # Should return empty

   # Disable swap
   sudo swapoff -a
   ```

2. **Sufficient RAM**: Minimum 2GB RAM + (50MB × max concurrent users)

3. **File Size Limits**: 50MB maximum file size enforced in application

#### Limitations and Caveats

- **Swap Risk**: If OS swap is enabled, RAM contents may be paged to disk under memory pressure
- **Cold Boot Attack**: Theoretical risk if physical RAM is extracted within seconds of processing
- **Memory Dumps**: Root access during processing could expose data in RAM

#### Verification

```bash
# Check if swap is enabled
free -h | grep Swap

# Monitor temp directory during processing
watch -n 1 'ls -la /tmp/*.pdf /tmp/*.docx 2>/dev/null | wc -l'
```

### Network Security

- API calls use HTTPS endpoints
- Timeout values are set for all external requests
- Error handling prevents leaking sensitive information

### Input Validation

- All user inputs are validated and sanitized
- File uploads are restricted to specific formats
- Size limits are enforced for document processing (50MB max)

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