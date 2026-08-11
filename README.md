# Automated Invoice Processing POC

## OCI Document Understanding + FastAPI + PeopleSoft Integration

This project is a proof of concept for automating invoice processing using **Oracle Cloud Infrastructure (OCI) Document Understanding**, **OCI Object Storage**, **Python/FastAPI**, and eventually **PeopleSoft**.

The application accepts invoice images or PDF documents, stores them in OCI Object Storage, sends them to OCI Document Understanding for extraction, converts the OCI response into a standardized invoice JSON structure, performs validation checks, and prepares the resulting data for future PeopleSoft voucher integration.

---

## 1. Project Objective

The objective of this POC is to reduce manual invoice data entry by automatically extracting and validating invoice information before sending it to PeopleSoft.

The target workflow is:

```text
Invoice
   |
   v
FastAPI Application
   |
   v
OCI Object Storage
(invoice-poc-input)
   |
   v
OCI Document Understanding
   |
   v
Raw OCI Extraction
   |
   v
Invoice Normalization
   |
   v
Validation / Review
   |
   v
Normalized Invoice JSON
   |
   v
OCI Object Storage
(invoice-poc-output)
   |
   v
PeopleSoft Mapper
   |
   v
PeopleSoft Voucher Integration
```

The PeopleSoft integration is a planned phase and is not yet implemented.

---

## 2. Current POC Status

The following functionality has been implemented.

### Completed

- FastAPI application setup
- Invoice upload API
- Local invoice upload handling
- File validation
- OCI SDK configuration
- OCI Object Storage integration
- Input bucket integration
- Output bucket integration
- OCI Document Understanding integration
- Invoice key-value extraction
- Invoice table / line-item extraction
- OCI response normalization
- Standard invoice JSON model
- Currency inference
- Date normalization
- Monetary value normalization
- Invoice-level arithmetic validation
- Line-level arithmetic validation
- Confidence-based warnings
- Required-field validation
- `READY` / `REVIEW_REQUIRED` processing status
- Normalized JSON storage in OCI Object Storage

### In Progress

- Improving extraction accuracy across different invoice layouts
- Supplier/vendor identification
- Complex invoice table handling
- Line-item extraction accuracy
- Additional validation rules
- Testing against multiple invoice formats

### Planned

- Invoice review interface
- Human correction / approval workflow
- Vendor validation
- Purchase Order matching
- PeopleSoft field mapping
- PeopleSoft voucher payload generation
- PeopleSoft API / Integration Broker integration
- Error handling and retry workflow
- Processing history / audit trail

---

## 3. Technology Stack

| Component | Technology |
|---|---|
| Backend API | FastAPI |
| Programming Language | Python |
| Validation | Pydantic |
| Cloud Platform | Oracle Cloud Infrastructure |
| Document Processing | OCI Document Understanding |
| File Storage | OCI Object Storage |
| Web Server | Uvicorn |
| Configuration | Pydantic Settings / `.env` |
| Source Control | Git / GitHub |
| Target ERP | PeopleSoft |

---

## 4. Project Architecture

The current architecture separates document processing into several responsibilities.

```text
                   +----------------------+
                   |       Invoice        |
                   |    PDF / PNG / JPG   |
                   +----------+-----------+
                              |
                              v
                   +----------------------+
                   |       FastAPI        |
                   |   /invoices/upload   |
                   +----------+-----------+
                              |
                              v
                   +----------------------+
                   |   Local Validation   |
                   |     and Storage      |
                   +----------+-----------+
                              |
                              v
                   +----------------------+
                   | OCI Object Storage   |
                   | invoice-poc-input    |
                   +----------+-----------+
                              |
                              v
                   +----------------------+
                   | OCI Document         |
                   | Understanding        |
                   +----------+-----------+
                              |
                              v
                   +----------------------+
                   | Raw OCI Extraction   |
                   +----------+-----------+
                              |
                              v
                   +----------------------+
                   | invoice_mapper.py    |
                   |                      |
                   | Normalize            |
                   | Parse Dates          |
                   | Parse Amounts        |
                   | Extract Lines        |
                   +----------+-----------+
                              |
                              v
                   +----------------------+
                   | Validation Layer     |
                   |                      |
                   | Confidence           |
                   | Required Fields      |
                   | Arithmetic           |
                   | Line Validation      |
                   +----------+-----------+
                              |
                     +--------+--------+
                     |                 |
                     v                 v
              +-------------+   +-----------------+
              |    READY    |   | REVIEW_REQUIRED |
              +------+------+   +--------+--------+
                     |                   |
                     +---------+---------+
                               |
                               v
                   +----------------------+
                   | OCI Object Storage   |
                   | invoice-poc-output   |
                   | normalized/*.json    |
                   +----------+-----------+
                              |
                              v
                   +----------------------+
                   | PeopleSoft Mapper    |
                   |     (Planned)        |
                   +----------+-----------+
                              |
                              v
                   +----------------------+
                   |      PeopleSoft      |
                   +----------------------+
```

---

## 5. Project Structure

A simplified project structure is:

```text
invoice-poc/
│
├── app/
│   ├── main.py
│   ├── config.py
│   ├── models.py
│   ├── storage.py
│   ├── oci_client.py
│   ├── invoice_mapper.py
│   │
│   └── routes/
│       └── invoices.py
│
├── uploads/
│
├── output/
│
├── static/
│
├── templates/
│
├── tests/
│
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
└── test_oci_upload.py
```

---

## 6. Main Application Components

### `app/main.py`

This is the main FastAPI application entry point.

Responsibilities include:

- creating the FastAPI application
- loading application configuration
- registering API routes
- configuring application metadata
- starting the backend application

The development server can be started with:

```bash
python -m uvicorn app.main:app --reload
```

---

### `app/config.py`

Contains application configuration using environment variables.

Configuration includes values such as:

- application name
- environment
- upload directory
- output directory
- maximum upload size
- OCI configuration profile
- OCI compartment ID
- OCI input bucket
- OCI output bucket

Sensitive values should be stored in `.env` and must not be committed to GitHub.

---

### `app/models.py`

Contains the application's Pydantic data models.

The primary purpose is to define the standardized structure expected for an invoice.

This allows extracted data to be validated before it is used by later processing stages.

---

### `app/storage.py`

Handles uploaded invoice files.

Responsibilities include:

- validating uploaded files
- checking allowed file types
- checking file size
- generating unique document IDs
- saving uploaded invoices locally

The generated document ID is used to track an invoice throughout the processing workflow.

---

### `app/oci_client.py`

Contains the integration with Oracle Cloud Infrastructure.

Responsibilities include:

1. Loading OCI credentials.
2. Creating the OCI Object Storage client.
3. Creating the OCI Document Understanding client.
4. Uploading invoices to the input bucket.
5. Sending documents to OCI Document Understanding.
6. Receiving the extraction response.
7. Passing the response to the invoice mapper.
8. Creating the final application document.
9. Uploading normalized JSON to the output bucket.

The current OCI buckets are logically separated into:

```text
invoice-poc-input
```

for source invoice documents and:

```text
invoice-poc-output
```

for normalized processing results.

Normalized results are stored using a structure similar to:

```text
normalized/<document-id>.json
```

---

### `app/invoice_mapper.py`

This component converts the OCI Document Understanding response into the standardized invoice model used by the application.

Responsibilities include:

- locating OCI document fields
- extracting field values
- retrieving extraction confidence
- normalizing dates
- normalizing monetary values
- extracting currency
- extracting line items
- performing invoice arithmetic validation
- performing line-item arithmetic validation
- detecting missing required fields
- generating review warnings

This component is currently one of the main areas being improved because invoice layouts can vary significantly between suppliers.

---

### `app/routes/invoices.py`

Contains the invoice API endpoints.

The primary endpoint is:

```http
POST /invoices/upload
```

The endpoint performs the processing workflow:

```text
Upload invoice
      |
      v
Save locally
      |
      v
Upload to OCI
      |
      v
Analyze with Document Understanding
      |
      v
Normalize extraction
      |
      v
Validate invoice
      |
      v
Store normalized JSON
      |
      v
Return processing result
```

---

## 7. OCI Services

### OCI Object Storage

Two buckets are currently used.

#### Input Bucket

```text
invoice-poc-input
```

Stores the original invoice document uploaded by the application.

Example:

```text
invoice-poc-input/
    85b1ab878e2343f1b02b79de85bc6d41.png
```

#### Output Bucket

```text
invoice-poc-output
```

Stores normalized JSON generated after document processing.

Example:

```text
invoice-poc-output/
    normalized/
        85b1ab878e2343f1b02b79de85bc6d41.json
```

---

## 8. OCI Document Understanding

OCI Document Understanding is used to analyze invoice documents.

The POC currently uses invoice extraction capabilities to identify information such as:

- supplier/vendor
- invoice number
- invoice date
- due date
- purchase order number
- invoice total
- tax
- payment terms
- line-item descriptions
- quantities
- unit prices
- line amounts

Document Understanding returns the extraction result to the application.

The raw OCI structure is then transformed by `invoice_mapper.py`.

---

## 9. Normalized Invoice Data Model

The application uses a standardized invoice structure independent of the original invoice layout.

Example:

```json
{
  "supplier_name": "Example Supplier",
  "supplier_tax_id": null,
  "remit_to_address": "100 Main Street, Phoenix, AZ 85001",
  "invoice_number": "INV-10025",
  "invoice_date": "2026-07-24",
  "po_number": "PO-45891",
  "currency_code": "USD",
  "gross_amount": 1125.50,
  "tax_amount": 75.50,
  "freight_amount": 50.00,
  "discount_amount": 0,
  "misc_charge_amount": 0,
  "payment_terms": "Net 30",
  "due_date": "2026-08-23",
  "line_items": [
    {
      "line_number": 1,
      "item_id": "ITEM-100",
      "description": "Example Item",
      "quantity": 5,
      "unit_of_measure": "EA",
      "unit_price": 200.00,
      "line_amount": 1000.00,
      "po_line_number": 1
    }
  ]
}
```

This normalized model is intended to become the source structure for the future PeopleSoft mapper.

---

## 10. Final Processing Document

The application stores additional processing information around the normalized invoice.

Example:

```json
{
  "document_id": "example-document-id",
  "processing_status": "REVIEW_REQUIRED",
  "source": {
    "bucket": "invoice-poc-input",
    "object_name": "example-document-id.png"
  },
  "invoice": {
    "supplier_name": "Example Supplier",
    "invoice_number": "INV-10025",
    "invoice_date": "2026-07-24",
    "currency_code": "USD",
    "gross_amount": 1125.50,
    "line_items": []
  },
  "validation": {
    "warnings": [],
    "field_metadata": {}
  }
}
```

---

## 11. Processing Status

The application currently supports two logical processing states.

### `READY`

The invoice passed the current validation rules and no review warnings were generated.

```json
{
  "processing_status": "READY"
}
```

This does not necessarily mean the invoice is ready for automatic PeopleSoft posting yet. More business validation will be introduced before production use.

### `REVIEW_REQUIRED`

One or more potential issues were detected.

```json
{
  "processing_status": "REVIEW_REQUIRED"
}
```

Examples include:

- missing required fields
- low extraction confidence
- ambiguous dates
- inferred currency
- invoice arithmetic mismatch
- line-item arithmetic mismatch

---

## 12. Validation Strategy

Document extraction should not automatically be trusted simply because OCI returned a value.

The application therefore applies a validation layer after extraction.

### Required Fields

Current important fields include:

```text
supplier_name
invoice_number
invoice_date
gross_amount
```

Missing required information triggers review.

### Confidence Validation

OCI extraction confidence can be evaluated for important fields.

Examples include:

- supplier
- invoice number
- invoice date
- invoice total
- PO number

Low-confidence values can trigger review.

### Invoice Arithmetic Validation

The application compares extracted line totals and charges against the invoice total.

Conceptually:

```text
Line Items
+ Tax
+ Freight
+ Miscellaneous Charges
- Discounts
-------------------------
Expected Invoice Total
```

The expected amount is compared with the extracted gross invoice amount.

A mismatch causes the invoice to be marked for review.

### Line-Level Validation

When quantity and unit price are available:

```text
Quantity × Unit Price = Line Amount
```

A mismatch generates a warning.

---

## 13. Monetary Value Handling

Invoice amounts may be returned by OCR in different formats.

Examples:

```text
2500.00
$2,500.00
$2 500.00
€1,250.00
£500.00
(250.00)
```

The mapper converts monetary values into a consistent numeric representation before validation.

`Decimal` is used instead of standard floating-point arithmetic for monetary calculations.

---

## 14. Date Handling

Invoices can contain dates in many formats.

Examples:

```text
11/02/2019
2019-02-11
Aug 31, 2013
August 31, 2013
Sep 30, 2013
```

The mapper converts recognized dates into:

```text
YYYY-MM-DD
```

Example:

```text
Aug 31, 2013
```

becomes:

```text
2013-08-31
```

Ambiguous numeric dates may require additional business rules or manual review.

---

## 15. Known Limitations

The current implementation is a POC and is not production-ready.

### Supplier Identification

Complex invoices may contain:

- supplier information
- bill-to information
- ship-to information
- remit-to information

Document extraction may occasionally confuse these entities.

Additional supplier validation will be required.

### Complex Tables

Some invoices contain multiple tables, such as:

- invoice line items
- project summaries
- fee summaries
- previous billing
- remaining balances
- tax summaries

OCI may classify some non-line-item tables as invoice line items.

Additional table classification and validation logic is required.

### Currency Inference

The current POC can infer currency from symbols such as:

```text
$
€
£
```

However, `$` does not uniquely identify USD.

Production logic should use stronger evidence such as:

- explicit currency code
- supplier information
- purchase order currency
- PeopleSoft supplier data

### Date Ambiguity

A date such as:

```text
11/02/2019
```

could represent either:

```text
11 February 2019
```

or:

```text
November 2, 2019
```

Future validation should use supplier or business context to resolve ambiguous formats.

### Line Item Extraction

Different suppliers use different invoice layouts.

Additional testing is required before automatically sending extracted lines to PeopleSoft.

---

## 16. Local Development Setup

### Prerequisites

Install:

- Python
- Git
- OCI Python SDK
- OCI API credentials

Clone the repository:

```bash
git clone <repository-url>
cd invoice-automation-poc
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## 17. Environment Configuration

Create `.env` from the example:

```bash
cp .env.example .env
```

Configure the required values locally.

Example:

```env
APP_NAME=Invoice Processing POC
ENVIRONMENT=development

OCI_CONFIG_PROFILE=DEFAULT
OCI_COMPARTMENT_ID=your-compartment-ocid

INPUT_BUCKET=invoice-poc-input
OUTPUT_BUCKET=invoice-poc-output

MAX_UPLOAD_SIZE_MB=20
```

Do not commit the real `.env` file.

---

## 18. OCI Authentication

OCI SDK authentication uses the local OCI configuration.

Typical location:

```text
~/.oci/config
```

Example structure:

```ini
[DEFAULT]
user=<OCI_USER_OCID>
fingerprint=<API_KEY_FINGERPRINT>
tenancy=<TENANCY_OCID>
region=us-phoenix-1
key_file=~/.oci/oci_api_key.pem
```

Never commit:

```text
~/.oci/config
*.pem
private keys
real OCI credentials
```

---

## 19. Running the Application

From the project root:

```bash
python -m uvicorn app.main:app --reload
```

The development server should start at:

```text
http://127.0.0.1:8000
```

Swagger API documentation is available at:

```text
http://127.0.0.1:8000/docs
```

---

## 20. Testing Invoice Upload

Open:

```text
http://127.0.0.1:8000/docs
```

Find:

```text
POST /invoices/upload
```

Select **Try it out**.

Upload an invoice image or PDF and execute the request.

The application will:

1. validate the uploaded file
2. generate a document ID
3. save the invoice locally
4. upload the invoice to OCI Object Storage
5. send it to OCI Document Understanding
6. receive extracted fields
7. normalize the extracted data
8. run validation checks
9. determine processing status
10. save normalized JSON to the output bucket
11. return the processing result through the API

---

## 21. Example API Response

```json
{
  "status": "REVIEW_REQUIRED",
  "document_id": "example-document-id",
  "original_filename": "invoice.png",
  "oci_input_bucket": "invoice-poc-input",
  "oci_input_object": "example-document-id.png",
  "oci_output_bucket": "invoice-poc-output",
  "oci_output_object": "normalized/example-document-id.json",
  "result": {
    "document_id": "example-document-id",
    "processing_status": "REVIEW_REQUIRED",
    "invoice": {},
    "validation": {
      "warnings": []
    }
  }
}
```

---

## 22. Security

The repository must not contain sensitive OCI credentials or real invoice data.

The `.gitignore` should exclude at minimum:

```gitignore
.env
.env.*
!.env.example

.venv/
venv/

__pycache__/
*.pyc

*.pem
*.key

uploads/*
!uploads/.gitkeep

output/*
!output/.gitkeep

.DS_Store
```

Before committing changes, verify:

```bash
git status
```

Never commit:

- `.env`
- OCI private keys
- OCI configuration credentials
- production invoice documents
- confidential extracted invoice data
- passwords or access tokens

---

## 23. Current Development Roadmap

### Phase 1 — Application Foundation

**Status: Completed**

- FastAPI application
- project structure
- Pydantic models
- upload endpoint
- local storage
- basic validation

### Phase 2 — OCI Integration

**Status: Completed / Being Improved**

- OCI authentication
- Object Storage integration
- input bucket
- output bucket
- Document Understanding integration
- invoice extraction
- normalized JSON
- confidence metadata
- arithmetic validation

### Phase 3 — Extraction Accuracy

**Status: Current Phase**

Test invoices from multiple suppliers and layouts.

For every test invoice, compare:

```text
Actual Invoice
      |
      v
OCI Extraction
      |
      v
Normalized JSON
```

Focus areas:

- supplier accuracy
- invoice number
- invoice date
- PO number
- invoice total
- tax
- currency
- due date
- line descriptions
- quantities
- unit prices
- line amounts

The goal is to determine whether an error originates from:

```text
OCI extraction
       vs.
normalization
       vs.
validation/business rules
```

### Phase 4 — Review Workflow

**Planned**

Build a review interface allowing a user to:

- view the original invoice
- view extracted fields
- see confidence levels
- see validation warnings
- correct extracted values
- approve or reject an invoice

### Phase 5 — PeopleSoft Mapping

**Planned**

After extraction accuracy is considered acceptable, create a dedicated PeopleSoft mapper.

Conceptually:

```text
Normalized Invoice
        |
        v
PeopleSoft Mapper
        |
        v
PeopleSoft Voucher Payload
```

The mapper will translate application fields into the fields required by the PeopleSoft integration.

### Phase 6 — PeopleSoft Validation

**Planned**

Potential validation includes:

- supplier lookup
- supplier location
- purchase order lookup
- PO line validation
- currency validation
- duplicate invoice detection
- accounting information
- voucher business rules

### Phase 7 — PeopleSoft Integration

**Planned**

Send validated invoices to the appropriate PeopleSoft integration interface.

Expected workflow:

```text
Invoice
   |
   v
OCI Extraction
   |
   v
Normalization
   |
   v
Validation
   |
   v
Human Review if Required
   |
   v
PeopleSoft Mapping
   |
   v
PeopleSoft Integration
   |
   v
Voucher Created
```

---

## 24. Important Design Principle

OCI Document Understanding should be treated as an **extraction engine**, not as the final source of truth.

The architecture intentionally separates:

```text
Document Extraction
        |
        v
Normalization
        |
        v
Validation
        |
        v
Business Rules
        |
        v
PeopleSoft Mapping
```

This separation allows the system to identify and correct extraction problems before invoice data reaches PeopleSoft.

---

## 25. Testing Strategy

Before implementing automatic PeopleSoft voucher creation, the system should be tested against a representative invoice dataset.

Recommended test cases include:

- different suppliers
- different invoice templates
- PNG invoices
- JPG invoices
- PDF invoices
- multi-page invoices
- PO invoices
- non-PO invoices
- invoices with tax
- invoices without tax
- invoices with freight
- invoices with discounts
- invoices with different currencies
- invoices with multiple tables
- invoices with complex line items
- invoices with ambiguous dates

For each invoice, compare expected values against normalized values.

Example:

```text
Field              Expected          Extracted          Result

Supplier           ABC Supplies      ABC Supplies       PASS
Invoice Number     INV-10025         INV-10025          PASS
Invoice Date       2026-07-24        2026-07-24         PASS
PO Number          PO-45891          PO-45891           PASS
Invoice Total      1125.50           1125.50            PASS
```

This testing phase should be completed before enabling automatic PeopleSoft processing.

---

## 26. Future Improvements

Potential improvements include:

- automated extraction accuracy testing
- configurable confidence thresholds
- vendor-specific extraction rules
- supplier master-data validation
- PO matching
- duplicate invoice detection
- smarter currency detection
- complex table classification
- human review UI
- approval workflow
- audit logging
- retry handling
- processing history
- monitoring and alerting
- PeopleSoft voucher creation
- automated integration tests
- deployment to OCI

---

## 27. Disclaimer

This project is currently a **proof of concept**.

Extracted invoice values must not be assumed to be correct solely because they were returned by OCI Document Understanding.

Invoices marked `REVIEW_REQUIRED` require validation before downstream processing.

Automatic PeopleSoft voucher creation should only be enabled after extraction accuracy, validation rules, security requirements, and business requirements have been sufficiently tested and approved.