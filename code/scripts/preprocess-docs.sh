#!/bin/bash
# Preprocess documents with docmark before upload to RAG

set -e

DOCS_DIR="${1:-/project/data/documents}"
OUTPUT_DIR="${2:-/project/data/documents_preprocessed}"
CLEANING_LEVEL="${DOCMARK_CLEANING_LEVEL:-medium}"

echo "========================================="
echo "docmark RAG Preprocessing"
echo "========================================="
echo "Input:  $DOCS_DIR"
echo "Output: $OUTPUT_DIR"
echo "Level:  $CLEANING_LEVEL"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Test docmark server
echo "Testing docmark server..."
python3 << EOF
import sys
sys.path.insert(0, '/project/code/scripts/helpers')
from docmark_client import DocmarkClient

client = DocmarkClient()
if not client.health_check():
    print('❌ docmark server not available!')
    print(f'   Server URL: {client.server_url}')
    print('')
    print('   To start the server:')
    print('   1. On Windows: cd C:\\Users\\kjfle\\Workspace\\docmark')
    print('   2. Activate venv: .venv\\Scripts\\activate')
    print('   3. Start server: python -m docmark.mcp_http_server')
    print('')
    print('   Then set DOCMARK_SERVER_URL if needed:')
    print('   export DOCMARK_SERVER_URL=http://host.docker.internal:8001')
    sys.exit(1)
print('✅ Server healthy')
EOF

if [ $? -ne 0 ]; then
    exit 1
fi

# Process all PDFs
echo ""
echo "Processing PDFs..."
python3 << EOF
import sys
sys.path.insert(0, '/project/code/scripts/helpers')
from pathlib import Path
from docmark_client import DocmarkClient
from tqdm import tqdm

client = DocmarkClient()
input_dir = Path("$DOCS_DIR")
output_dir = Path("$OUTPUT_DIR")

# Find all PDFs
pdf_files = list(input_dir.rglob("*.pdf"))

if not pdf_files:
    print("No PDF files found in $DOCS_DIR")
    sys.exit(0)

print(f"Found {len(pdf_files)} PDF files\n")

# Process each
success_count = 0
failed_count = 0

for pdf_path in tqdm(pdf_files, desc="Converting"):
    # Preserve directory structure
    rel_path = pdf_path.relative_to(input_dir)
    out_path = output_dir / rel_path.with_suffix('.md')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        client.convert_document(
            file_path=str(pdf_path),
            output_path=str(out_path),
            rag_mode=True,
            rag_cleaning_level="$CLEANING_LEVEL",
            enhanced_pdf=True,
            preflight=True,
        )
        success_count += 1
    except Exception as e:
        print(f"\n⚠️  Failed: {pdf_path.name}: {e}")
        failed_count += 1

print(f"\n✅ Preprocessing complete!")
print(f"   Success: {success_count} files")
if failed_count > 0:
    print(f"   Failed:  {failed_count} files")
print(f"   Output:  {output_dir}")
EOF

echo ""
echo "========================================="
echo "Next: Upload preprocessed files to RAG"
echo "  cp $OUTPUT_DIR/*.md $DOCS_DIR/"
echo "  bash /project/code/scripts/upload-docs.sh"
echo "========================================="
