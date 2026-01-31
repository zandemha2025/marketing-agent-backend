"""
Email Marketing Test Suite

Tests for:
1. Single email generation for each type
2. Email sequence generation
3. HTML validation
4. Plain text version verification
5. Subject line variations (3+)
6. File storage

Results saved to: test_results/email_marketing_test.json
"""
import asyncio
import json
import os
import re
import sys
from datetime import datetime
from typing import Dict, Any, List

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.content.email_generator import EmailGenerator, EmailType
from app.services.content.email_sequence import EmailSequenceGenerator, SequenceType


class EmailMarketingTestSuite:
    """Comprehensive test suite for email marketing functionality."""
    
    def __init__(self):
        self.email_generator = EmailGenerator()
        self.sequence_generator = EmailSequenceGenerator()
        self.results = {
            "test_run_timestamp": datetime.now().isoformat(),
            "tests": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
            }
        }
    
    def add_result(self, test_name: str, passed: bool, details: Dict[str, Any]):
        """Add a test result."""
        self.results["tests"].append({
            "name": test_name,
            "passed": passed,
            "details": details,
            "timestamp": datetime.now().isoformat(),
        })
        self.results["summary"]["total"] += 1
        if passed:
            self.results["summary"]["passed"] += 1
        else:
            self.results["summary"]["failed"] += 1
    
    def validate_html(self, html: str) -> Dict[str, Any]:
        """Validate HTML email structure."""
        checks = {
            "has_doctype": "<!DOCTYPE" in html.upper() or "<html" in html.lower(),
            "has_html_tag": "<html" in html.lower(),
            "has_body": "<body" in html.lower() or "<table" in html.lower(),
            "has_table_structure": "<table" in html.lower(),
            "has_inline_styles": "style=" in html.lower(),
            "max_width_600": "600" in html or "max-width" in html.lower(),
            "has_content": len(html) > 500,
        }
        return {
            "valid": all(checks.values()),
            "checks": checks,
            "html_length": len(html),
        }
    
    def validate_plain_text(self, text: str) -> Dict[str, Any]:
        """Validate plain text email."""
        checks = {
            "not_empty": len(text.strip()) > 0,
            "no_html_tags": "<" not in text or text.count("<") < 3,
            "has_content": len(text) > 50,
        }
        return {
            "valid": all(checks.values()),
            "checks": checks,
            "text_length": len(text),
        }
    
    async def test_single_email_generation(self, email_type: str) -> Dict[str, Any]:
        """Test single email generation for a specific type."""
        print(f"\n📧 Testing {email_type} email generation...")
        
        try:
            result = await self.email_generator.generate_complete_email(
                email_type=email_type,
                subject=f"Test {email_type.title()} Email",
                headline=f"Welcome to Our {email_type.title()} Email",
                body_content=f"This is a test {email_type} email with sample content. "
                            f"We're testing the email generation system to ensure it works correctly. "
                            f"This email should have proper HTML structure and plain text fallback.",
                cta_text="Learn More",
                cta_url="https://example.com/action",
                brand_colors={"primary": "#007bff"},
                campaign_id=f"test-{email_type}-001",
                save_to_file=True,
            )
            
            # Validate results
            html_validation = self.validate_html(result["html_content"])
            text_validation = self.validate_plain_text(result["text_content"])
            
            # Check subject lines
            subject_lines = result.get("subject_lines", [])
            has_multiple_subjects = len(subject_lines) >= 3
            
            # Check preview text
            has_preview_text = bool(result.get("preview_text"))
            
            # Check file was saved
            file_saved = bool(result.get("file_path"))
            
            passed = all([
                result.get("success"),
                html_validation["valid"],
                text_validation["valid"],
                has_multiple_subjects,
                has_preview_text,
            ])
            
            details = {
                "email_type": email_type,
                "email_id": result.get("email_id"),
                "html_validation": html_validation,
                "text_validation": text_validation,
                "subject_lines_count": len(subject_lines),
                "subject_lines": subject_lines,
                "preview_text": result.get("preview_text"),
                "preview_url": result.get("preview_url"),
                "file_path": result.get("file_path"),
                "file_saved": file_saved,
            }
            
            self.add_result(f"email_generation_{email_type}", passed, details)
            
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"  {status} - {email_type} email")
            print(f"    - HTML valid: {html_validation['valid']}")
            print(f"    - Text valid: {text_validation['valid']}")
            print(f"    - Subject lines: {len(subject_lines)}")
            print(f"    - Preview text: {has_preview_text}")
            print(f"    - File saved: {file_saved}")
            
            return details
            
        except Exception as e:
            self.add_result(f"email_generation_{email_type}", False, {
                "error": str(e),
                "email_type": email_type,
            })
            print(f"  ❌ FAILED - {email_type} email: {str(e)}")
            return {"error": str(e)}
    
    async def test_all_email_types(self) -> Dict[str, Any]:
        """Test email generation for all supported types."""
        print("\n" + "="*60)
        print("📧 TESTING ALL EMAIL TYPES")
        print("="*60)
        
        email_types = ["promotional", "welcome", "nurture", "newsletter", "transactional"]
        results = {}
        
        for email_type in email_types:
            results[email_type] = await self.test_single_email_generation(email_type)
        
        return results
    
    async def test_email_sequence_generation(self, sequence_type: str) -> Dict[str, Any]:
        """Test email sequence generation for a specific type."""
        print(f"\n📬 Testing {sequence_type} sequence generation...")
        
        try:
            seq_type = SequenceType(sequence_type)
            result = await self.sequence_generator.generate_sequence(
                sequence_type=seq_type,
                num_emails=5,
                brand_data={"primary_color": "#007bff", "font_family": "Arial"},
                campaign_id=f"test-sequence-{sequence_type}-001",
                save_to_file=True,
            )
            
            # Validate each email in the sequence
            email_validations = []
            for email in result.emails:
                html_valid = self.validate_html(email.html_content)
                text_valid = self.validate_plain_text(email.text_content)
                email_validations.append({
                    "day": email.day,
                    "position": email.position,
                    "subject": email.subject,
                    "html_valid": html_valid["valid"],
                    "text_valid": text_valid["valid"],
                    "theme": email.theme,
                })
            
            # Check timing schedule
            has_timing_schedule = len(result.timing_schedule) >= 5
            
            # Check all emails are valid
            all_emails_valid = all(e["html_valid"] and e["text_valid"] for e in email_validations)
            
            # Check unique content
            subjects = [e["subject"] for e in email_validations]
            unique_subjects = len(set(subjects)) == len(subjects)
            
            passed = all([
                len(result.emails) == 5,
                has_timing_schedule,
                all_emails_valid,
                unique_subjects,
            ])
            
            details = {
                "sequence_type": sequence_type,
                "sequence_id": result.sequence_id,
                "total_emails": result.total_emails,
                "timing_schedule": result.timing_schedule,
                "email_validations": email_validations,
                "all_emails_valid": all_emails_valid,
                "unique_subjects": unique_subjects,
                "file_path": result.file_path,
            }
            
            self.add_result(f"sequence_generation_{sequence_type}", passed, details)
            
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"  {status} - {sequence_type} sequence")
            print(f"    - Emails generated: {len(result.emails)}")
            print(f"    - Timing schedule: {result.timing_schedule}")
            print(f"    - All emails valid: {all_emails_valid}")
            print(f"    - Unique subjects: {unique_subjects}")
            
            return details
            
        except Exception as e:
            self.add_result(f"sequence_generation_{sequence_type}", False, {
                "error": str(e),
                "sequence_type": sequence_type,
            })
            print(f"  ❌ FAILED - {sequence_type} sequence: {str(e)}")
            return {"error": str(e)}
    
    async def test_all_sequence_types(self) -> Dict[str, Any]:
        """Test sequence generation for all supported types."""
        print("\n" + "="*60)
        print("📬 TESTING ALL SEQUENCE TYPES")
        print("="*60)
        
        sequence_types = ["welcome", "nurture", "onboarding", "re_engagement"]
        results = {}
        
        for seq_type in sequence_types:
            results[seq_type] = await self.test_email_sequence_generation(seq_type)
        
        return results
    
    async def test_subject_line_variations(self) -> Dict[str, Any]:
        """Test that subject line variations are generated correctly."""
        print("\n" + "="*60)
        print("📝 TESTING SUBJECT LINE VARIATIONS")
        print("="*60)
        
        try:
            # Generate an email and check subject lines
            result = await self.email_generator.generate_complete_email(
                email_type="promotional",
                subject="Amazing Summer Sale - 50% Off Everything",
                headline="Summer Sale",
                body_content="Don't miss our biggest sale of the year!",
                cta_text="Shop Now",
                cta_url="https://example.com/sale",
                brand_colors={"primary": "#ff6b6b"},
                save_to_file=False,
            )
            
            subject_lines = result.get("subject_lines", [])
            
            # Validate subject lines
            checks = {
                "has_3_or_more": len(subject_lines) >= 3,
                "all_non_empty": all(len(s.strip()) > 0 for s in subject_lines),
                "all_under_100_chars": all(len(s) < 100 for s in subject_lines),
                "has_variety": len(set(subject_lines)) == len(subject_lines),
            }
            
            passed = all(checks.values())
            
            details = {
                "subject_lines": subject_lines,
                "count": len(subject_lines),
                "checks": checks,
            }
            
            self.add_result("subject_line_variations", passed, details)
            
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"  {status} - Subject line variations")
            print(f"    - Count: {len(subject_lines)}")
            print(f"    - Lines: {subject_lines}")
            
            return details
            
        except Exception as e:
            self.add_result("subject_line_variations", False, {"error": str(e)})
            print(f"  ❌ FAILED - Subject line variations: {str(e)}")
            return {"error": str(e)}
    
    async def test_responsive_email_design(self) -> Dict[str, Any]:
        """Test that emails have responsive design elements."""
        print("\n" + "="*60)
        print("📱 TESTING RESPONSIVE EMAIL DESIGN")
        print("="*60)
        
        try:
            result = await self.email_generator.generate_complete_email(
                email_type="newsletter",
                subject="Monthly Newsletter",
                headline="What's New This Month",
                body_content="Check out our latest updates and news.",
                cta_text="Read More",
                cta_url="https://example.com/newsletter",
                brand_colors={"primary": "#4a90d9"},
                save_to_file=False,
            )
            
            html = result.get("html_content", "")
            
            # Check for responsive design elements
            checks = {
                "has_max_width": "max-width" in html.lower() or "600" in html,
                "has_table_layout": "<table" in html.lower(),
                "has_inline_styles": "style=" in html.lower(),
                "has_width_100_percent": "100%" in html,
                "mobile_friendly_structure": "cellpadding" in html.lower() or "cellspacing" in html.lower(),
            }
            
            passed = sum(checks.values()) >= 3  # At least 3 responsive elements
            
            details = {
                "checks": checks,
                "responsive_score": sum(checks.values()),
                "html_length": len(html),
            }
            
            self.add_result("responsive_email_design", passed, details)
            
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"  {status} - Responsive email design")
            print(f"    - Responsive score: {sum(checks.values())}/5")
            for check, value in checks.items():
                print(f"    - {check}: {'✓' if value else '✗'}")
            
            return details
            
        except Exception as e:
            self.add_result("responsive_email_design", False, {"error": str(e)})
            print(f"  ❌ FAILED - Responsive email design: {str(e)}")
            return {"error": str(e)}
    
    async def test_file_storage(self) -> Dict[str, Any]:
        """Test that emails are saved to the correct location."""
        print("\n" + "="*60)
        print("💾 TESTING FILE STORAGE")
        print("="*60)
        
        try:
            result = await self.email_generator.generate_complete_email(
                email_type="welcome",
                subject="Welcome to Our Platform",
                headline="Welcome!",
                body_content="We're excited to have you join us.",
                cta_text="Get Started",
                cta_url="https://example.com/start",
                brand_colors={"primary": "#28a745"},
                campaign_id="test-storage-001",
                save_to_file=True,
            )
            
            file_path = result.get("file_path")
            
            # Check if files exist
            checks = {
                "file_path_returned": bool(file_path),
                "directory_exists": os.path.isdir(file_path) if file_path else False,
                "html_file_exists": os.path.isfile(os.path.join(file_path, "email.html")) if file_path else False,
                "text_file_exists": os.path.isfile(os.path.join(file_path, "email.txt")) if file_path else False,
                "metadata_exists": os.path.isfile(os.path.join(file_path, "metadata.json")) if file_path else False,
                "preview_exists": os.path.isfile(os.path.join(file_path, "preview.html")) if file_path else False,
            }
            
            passed = all(checks.values())
            
            # Read metadata if exists
            metadata = None
            if checks["metadata_exists"]:
                with open(os.path.join(file_path, "metadata.json")) as f:
                    metadata = json.load(f)
            
            details = {
                "file_path": file_path,
                "checks": checks,
                "metadata": metadata,
            }
            
            self.add_result("file_storage", passed, details)
            
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"  {status} - File storage")
            print(f"    - Path: {file_path}")
            for check, value in checks.items():
                print(f"    - {check}: {'✓' if value else '✗'}")
            
            return details
            
        except Exception as e:
            self.add_result("file_storage", False, {"error": str(e)})
            print(f"  ❌ FAILED - File storage: {str(e)}")
            return {"error": str(e)}
    
    def save_results(self):
        """Save test results to JSON file."""
        # Create test_results directory
        results_dir = "test_results"
        os.makedirs(results_dir, exist_ok=True)
        
        # Save results
        results_path = os.path.join(results_dir, "email_marketing_test.json")
        with open(results_path, "w") as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\n📄 Results saved to: {results_path}")
        return results_path
    
    async def run_all_tests(self):
        """Run all email marketing tests."""
        print("\n" + "="*60)
        print("🚀 EMAIL MARKETING TEST SUITE")
        print("="*60)
        print(f"Started at: {datetime.now().isoformat()}")
        
        # Run all tests
        await self.test_all_email_types()
        await self.test_all_sequence_types()
        await self.test_subject_line_variations()
        await self.test_responsive_email_design()
        await self.test_file_storage()
        
        # Print summary
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        print(f"Total tests: {self.results['summary']['total']}")
        print(f"Passed: {self.results['summary']['passed']} ✅")
        print(f"Failed: {self.results['summary']['failed']} ❌")
        print(f"Success rate: {self.results['summary']['passed'] / self.results['summary']['total'] * 100:.1f}%")
        
        # Save results
        results_path = self.save_results()
        
        return self.results


async def main():
    """Run the email marketing test suite."""
    suite = EmailMarketingTestSuite()
    results = await suite.run_all_tests()
    
    # Exit with appropriate code
    if results["summary"]["failed"] > 0:
        print("\n⚠️  Some tests failed. Check the results file for details.")
        sys.exit(1)
    else:
        print("\n✅ All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
