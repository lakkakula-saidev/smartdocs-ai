#!/usr/bin/env python3
"""
End-to-End Validation Script for SmartDocs AI
Tests the complete flow from frontend API client perspective
"""

import requests
import json
import time
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

class ValidationResults:
    def __init__(self):
        self.tests = []
        self.passed = 0
        self.failed = 0
        self.start_time = time.time()
    
    def add_test(self, name: str, passed: bool, details: str = "", error: str = ""):
        self.tests.append({
            "name": name,
            "passed": passed,
            "details": details,
            "error": error,
            "timestamp": time.time()
        })
        if passed:
            self.passed += 1
        else:
            self.failed += 1
    
    def print_summary(self):
        duration = time.time() - self.start_time
        print(f"\n{'='*60}")
        print(f"VALIDATION SUMMARY")
        print(f"{'='*60}")
        print(f"Total Tests: {len(self.tests)}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Duration: {duration:.2f}s")
        print(f"{'='*60}")
        
        if self.failed > 0:
            print("\nFAILED TESTS:")
            for test in self.tests:
                if not test["passed"]:
                    print(f"❌ {test['name']}: {test['error']}")
        
        return self.failed == 0

class SmartDocsValidator:
    def __init__(self, base_url: str = "http://0.0.0.0:8001"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Origin": "http://localhost:5173"  # Simulate frontend origin
        })
        self.results = ValidationResults()
        self.test_document_id = None
    
    def log(self, message: str):
        print(f"[{time.strftime('%H:%M:%S')}] {message}")
    
    def test_health_endpoint(self):
        """Test the health endpoint"""
        self.log("Testing health endpoint...")
        try:
            response = self.session.get(f"{self.base_url}/health")
            
            if response.status_code != 200:
                self.results.add_test("Health Endpoint Status", False, 
                                    error=f"Expected 200, got {response.status_code}")
                return
            
            data = response.json()
            required_fields = ["status", "has_documents", "document_count", "version"]
            missing_fields = [f for f in required_fields if f not in data]
            
            if missing_fields:
                self.results.add_test("Health Endpoint Response", False,
                                    error=f"Missing fields: {missing_fields}")
                return
            
            if data["status"] != "ok":
                self.results.add_test("Health Endpoint Status", False,
                                    error=f"Status is '{data['status']}', expected 'ok'")
                return
            
            self.results.add_test("Health Endpoint", True, 
                                details=f"Status: {data['status']}, Documents: {data['document_count']}")
            
        except Exception as e:
            self.results.add_test("Health Endpoint", False, error=str(e))
    
    def test_cors_headers(self):
        """Test CORS configuration"""
        self.log("Testing CORS configuration...")
        try:
            # Test preflight request
            response = self.session.options(f"{self.base_url}/health", headers={
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type"
            })
            
            cors_headers = {
                "access-control-allow-origin": response.headers.get("access-control-allow-origin"),
                "access-control-allow-methods": response.headers.get("access-control-allow-methods"),
                "access-control-allow-headers": response.headers.get("access-control-allow-headers")
            }
            
            # Check if CORS allows our frontend origin
            origin_header = cors_headers["access-control-allow-origin"]
            if origin_header and (origin_header == "*" or "localhost:5173" in origin_header):
                self.results.add_test("CORS Configuration", True,
                                    details=f"Allowed origins: {origin_header}")
            else:
                self.results.add_test("CORS Configuration", False,
                                    error=f"Frontend origin not allowed: {origin_header}")
                
        except Exception as e:
            self.results.add_test("CORS Configuration", False, error=str(e))
    
    def create_test_pdf(self) -> Optional[str]:
        """Create a simple test PDF file"""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            
            filename = "test_document.pdf"
            c = canvas.Canvas(filename, pagesize=letter)
            c.drawString(100, 750, "SmartDocs AI Test Document")
            c.drawString(100, 720, "This is a test document for validation.")
            c.drawString(100, 690, "It contains sample text for testing the upload and processing functionality.")
            c.drawString(100, 660, "The document should be processed and made available for questions.")
            c.drawString(100, 630, "")
            c.drawString(100, 600, "Key test information:")
            c.drawString(100, 570, "- Document processing pipeline")
            c.drawString(100, 540, "- Vector embedding creation")
            c.drawString(100, 510, "- Question answering capabilities")
            c.drawString(100, 480, "- End-to-end validation")
            c.save()
            
            return filename
            
        except ImportError:
            # Fallback: create a proper PDF using fpdf
            try:
                from fpdf import FPDF
                
                filename = "test_document.pdf"
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                pdf.cell(200, 10, txt="SmartDocs AI Test Document", ln=1, align="C")
                pdf.ln(10)
                pdf.cell(200, 10, txt="This is a test document for validation.", ln=1)
                pdf.cell(200, 10, txt="It contains sample text for testing the upload and processing functionality.", ln=1)
                pdf.cell(200, 10, txt="The document should be processed and made available for questions.", ln=1)
                pdf.ln(10)
                pdf.cell(200, 10, txt="Key test information:", ln=1)
                pdf.cell(200, 10, txt="- Document processing pipeline", ln=1)
                pdf.cell(200, 10, txt="- Vector embedding creation", ln=1)
                pdf.cell(200, 10, txt="- Question answering capabilities", ln=1)
                pdf.cell(200, 10, txt="- End-to-end validation", ln=1)
                pdf.output(filename)
                
                return filename
                
            except ImportError:
                self.log("Neither ReportLab nor fpdf available, skipping PDF creation test...")
                return None
            
        except Exception as e:
            self.log(f"Failed to create test document: {e}")
            return None
    
    def test_document_upload(self):
        """Test document upload functionality"""
        self.log("Testing document upload...")
        
        # Create test document
        test_file = self.create_test_pdf()
        if not test_file:
            self.results.add_test("Document Upload", False, error="Could not create test document")
            return
        
        try:
            # Test upload
            with open(test_file, "rb") as f:
                files = {"file": (test_file, f, "application/pdf")}
                headers = {"Origin": "http://localhost:5173"}  # Remove Content-Type for multipart
                
                response = requests.post(f"{self.base_url}/upload", files=files, headers=headers)
            
            if response.status_code not in [200, 201]:
                self.results.add_test("Document Upload", False,
                                    error=f"Upload failed with status {response.status_code}: {response.text}")
                return
            
            data = response.json()
            required_fields = ["document_id", "chunks", "bytes"]
            missing_fields = [f for f in required_fields if f not in data]
            
            if missing_fields:
                self.results.add_test("Document Upload", False,
                                    error=f"Missing response fields: {missing_fields}")
                return
            
            self.test_document_id = data["document_id"]
            self.results.add_test("Document Upload", True,
                                details=f"ID: {data['document_id'][:8]}..., Chunks: {data['chunks']}, Bytes: {data['bytes']}")
            
        except Exception as e:
            self.results.add_test("Document Upload", False, error=str(e))
        finally:
            # Cleanup test file
            if test_file and os.path.exists(test_file):
                os.remove(test_file)
    
    def test_question_answering(self):
        """Test question answering functionality"""
        if not self.test_document_id:
            self.results.add_test("Question Answering", False, error="No document uploaded for testing")
            return
        
        self.log("Testing question answering...")
        
        try:
            # Test question about the document
            payload = {
                "query": "What is this document about?",
                "document_id": self.test_document_id
            }
            
            response = self.session.post(f"{self.base_url}/ask", json=payload)
            
            if response.status_code != 200:
                self.results.add_test("Question Answering", False,
                                    error=f"Query failed with status {response.status_code}: {response.text}")
                return
            
            data = response.json()
            if "answer" not in data:
                self.results.add_test("Question Answering", False,
                                    error="Response missing 'answer' field")
                return
            
            answer = data["answer"]
            if len(answer.strip()) < 10:
                self.results.add_test("Question Answering", False,
                                    error=f"Answer too short: '{answer}'")
                return
            
            self.results.add_test("Question Answering", True,
                                details=f"Answer length: {len(answer)} chars")
            
        except Exception as e:
            self.results.add_test("Question Answering", False, error=str(e))
    
    def test_error_handling(self):
        """Test error handling scenarios"""
        self.log("Testing error handling...")
        
        # Test 1: Invalid document ID
        try:
            payload = {"query": "Test query", "document_id": "invalid-id"}
            response = self.session.post(f"{self.base_url}/ask", json=payload)
            
            if response.status_code == 200:
                self.results.add_test("Error Handling - Invalid Document", False,
                                    error="Should have failed with invalid document ID")
            else:
                data = response.json()
                if "detail" in data or "message" in data:
                    self.results.add_test("Error Handling - Invalid Document", True,
                                        details=f"Proper error response: {response.status_code}")
                else:
                    self.results.add_test("Error Handling - Invalid Document", False,
                                        error="Error response missing detail/message")
        except Exception as e:
            self.results.add_test("Error Handling - Invalid Document", False, error=str(e))
        
        # Test 2: Missing query
        try:
            payload = {"document_id": self.test_document_id} if self.test_document_id else {}
            response = self.session.post(f"{self.base_url}/ask", json=payload)
            
            if response.status_code == 200:
                self.results.add_test("Error Handling - Missing Query", False,
                                    error="Should have failed with missing query")
            else:
                self.results.add_test("Error Handling - Missing Query", True,
                                    details=f"Proper error response: {response.status_code}")
        except Exception as e:
            self.results.add_test("Error Handling - Missing Query", False, error=str(e))
    
    def test_response_formats(self):
        """Test that response formats match frontend expectations"""
        self.log("Testing response formats...")
        
        try:
            # Test health response format
            response = self.session.get(f"{self.base_url}/health")
            data = response.json()
            
            # Check for expected fields and types
            format_checks = [
                ("status", str),
                ("has_documents", bool),
                ("document_count", int),
                ("version", str)
            ]
            
            format_errors = []
            for field, expected_type in format_checks:
                if field not in data:
                    format_errors.append(f"Missing field: {field}")
                elif not isinstance(data[field], expected_type):
                    format_errors.append(f"Field {field} should be {expected_type.__name__}, got {type(data[field]).__name__}")
            
            if format_errors:
                self.results.add_test("Response Format - Health", False,
                                    error="; ".join(format_errors))
            else:
                self.results.add_test("Response Format - Health", True,
                                    details="All fields present with correct types")
                
        except Exception as e:
            self.results.add_test("Response Format - Health", False, error=str(e))
    
    def run_validation(self):
        """Run all validation tests"""
        print(f"Starting SmartDocs AI End-to-End Validation")
        print(f"Backend URL: {self.base_url}")
        print(f"{'='*60}")
        
        # Run all tests
        self.test_health_endpoint()
        self.test_cors_headers()
        self.test_response_formats()
        self.test_document_upload()
        self.test_question_answering()
        self.test_error_handling()
        
        # Print results
        return self.results.print_summary()

def main():
    """Main validation function"""
    base_url = os.getenv("BACKEND_URL", "http://0.0.0.0:8001")
    
    validator = SmartDocsValidator(base_url)
    success = validator.run_validation()
    
    # Write detailed results to file
    results_file = "validation_results.json"
    with open(results_file, "w") as f:
        json.dump({
            "timestamp": time.time(),
            "success": success,
            "summary": {
                "total": len(validator.results.tests),
                "passed": validator.results.passed,
                "failed": validator.results.failed
            },
            "tests": validator.results.tests
        }, f, indent=2)
    
    print(f"\nDetailed results written to: {results_file}")
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()