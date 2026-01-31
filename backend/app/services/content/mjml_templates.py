"""
MJML Template System for Email Generation

Provides:
- MJML-based templates for cross-email-client compatibility
- Brand DNA integration (colors, fonts)
- Multiple email types: Promotional, Newsletter, Welcome, Announcement, Nurture
- Output: HTML, MJML source, plaintext
"""
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import re

logger = logging.getLogger(__name__)


@dataclass
class EmailTemplate:
    """An email template with MJML structure."""
    name: str
    mjml_template: str
    description: str
    category: str  # "promotional", "newsletter", "welcome", "announcement", "nurture"


@dataclass
class GeneratedEmail:
    """A generated email with multiple output formats."""
    subject: str
    mjml: str
    html: str
    plaintext: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "subject": self.subject,
            "mjml": self.mjml,
            "html": self.html,
            "plaintext": self.plaintext,
            "metadata": self.metadata
        }


class MJMLTemplateSystem:
    """
    MJML-based email template system.
    
    Features:
    - Cross-email-client compatible templates
    - Brand DNA integration
    - Multiple email types
    - Subject line generation
    """
    
    def __init__(self):
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, EmailTemplate]:
        """Load all email templates."""
        return {
            "welcome": EmailTemplate(
                name="Welcome Email",
                category="welcome",
                description="Welcome new subscribers or customers",
                mjml_template=self._get_welcome_template()
            ),
            "newsletter": EmailTemplate(
                name="Newsletter",
                category="newsletter",
                description="Regular newsletter with multiple sections",
                mjml_template=self._get_newsletter_template()
            ),
            "promotional": EmailTemplate(
                name="Promotional",
                category="promotional",
                description="Sales and promotional offers",
                mjml_template=self._get_promotional_template()
            ),
            "announcement": EmailTemplate(
                name="Announcement",
                category="announcement",
                description="Product launches and company news",
                mjml_template=self._get_announcement_template()
            ),
            "nurture": EmailTemplate(
                name="Nurture Sequence",
                category="nurture",
                description="Educational and relationship building",
                mjml_template=self._get_nurture_template()
            ),
            "transactional": EmailTemplate(
                name="Transactional",
                category="transactional",
                description="Order confirmations, receipts, and account notifications",
                mjml_template=self._get_transactional_template()
            ),
        }
    
    def _get_base_template(self) -> str:
        """Get the base MJML template structure."""
        return '''<mjml>
  <mj-head>
    <mj-font name="{{font_family}}" href="https://fonts.googleapis.com/css?family={{font_family_url}}" />
    <mj-attributes>
      <mj-all font-family="{{font_family}}, Arial, sans-serif" />
      <mj-text font-size="16px" line-height="1.6" color="#333333" />
      <mj-button background-color="{{primary_color}}" color="white" font-weight="bold" border-radius="4px" />
    </mj-attributes>
    <mj-style>
      .header-logo { text-align: center; padding: 20px 0; }
      .footer-text { font-size: 12px; color: #666666; text-align: center; }
      .social-links { text-align: center; padding: 20px 0; }
    </mj-style>
  </mj-head>
  <mj-body background-color="#f4f4f4">
    {{content}}
  </mj-body>
</mjml>'''
    
    def _get_welcome_template(self) -> str:
        """Get welcome email template."""
        return '''<mj-section background-color="{{primary_color}}" padding="40px 20px">
      <mj-column>
        <mj-text align="center" color="white" font-size="28px" font-weight="bold">
          {{headline}}
        </mj-text>
        <mj-text align="center" color="white" font-size="18px">
          {{subheadline}}
        </mj-text>
      </mj-column>
    </mj-section>
    
    <mj-section background-color="white" padding="40px 30px">
      <mj-column>
        <mj-text font-size="20px" font-weight="bold" color="#333333">
          Hi {{first_name}},
        </mj-text>
        <mj-text>
          {{welcome_message}}
        </mj-text>
        <mj-text>
          {{body_content}}
        </mj-text>
        <mj-button href="{{cta_url}}" padding="30px 0">
          {{cta_text}}
        </mj-button>
        <mj-text>
          {{closing_message}}
        </mj-text>
      </mj-column>
    </mj-section>
    
    <mj-section background-color="#f8f8f8" padding="20px">
      <mj-column>
        <mj-text align="center" font-size="14px" color="#666666">
          {{footer_text}}
        </mj-text>
        <mj-text align="center" font-size="12px" color="#999999">
          {{company_address}}
        </mj-text>
        <mj-text align="center" font-size="12px" color="#999999">
          <a href="{{unsubscribe_url}}" style="color: #999999;">Unsubscribe</a>
        </mj-text>
      </mj-column>
    </mj-section>'''
    
    def _get_newsletter_template(self) -> str:
        """Get newsletter template."""
        return '''<mj-section background-color="{{primary_color}}" padding="30px 20px">
      <mj-column>
        <mj-text align="center" color="white" font-size="24px" font-weight="bold">
          {{newsletter_title}}
        </mj-text>
        <mj-text align="center" color="white" font-size="14px">
          {{issue_date}}
        </mj-text>
      </mj-column>
    </mj-section>
    
    <mj-section background-color="white" padding="30px">
      <mj-column>
        <mj-text font-size="22px" font-weight="bold" color="#333333">
          {{headline}}
        </mj-text>
        <mj-text>
          {{intro_text}}
        </mj-text>
      </mj-column>
    </mj-section>
    
    {{articles}}
    
    <mj-section background-color="#f8f8f8" padding="30px">
      <mj-column>
        <mj-text align="center" font-size="18px" font-weight="bold">
          {{cta_section_title}}
        </mj-text>
        <mj-text align="center">
          {{cta_section_text}}
        </mj-text>
        <mj-button href="{{cta_url}}">
          {{cta_text}}
        </mj-button>
      </mj-column>
    </mj-section>
    
    <mj-section background-color="#333333" padding="20px">
      <mj-column>
        <mj-text align="center" color="white" font-size="12px">
          {{footer_text}}
        </mj-text>
        <mj-text align="center" color="#999999" font-size="11px">
          <a href="{{unsubscribe_url}}" style="color: #999999;">Unsubscribe</a> |
          <a href="{{preferences_url}}" style="color: #999999;">Preferences</a>
        </mj-text>
      </mj-column>
    </mj-section>'''
    
    def _get_promotional_template(self) -> str:
        """Get promotional email template."""
        return '''<mj-section background-color="{{primary_color}}" padding="40px 20px">
      <mj-column>
        <mj-text align="center" color="white" font-size="32px" font-weight="bold">
          {{headline}}
        </mj-text>
        <mj-text align="center" color="white" font-size="20px">
          {{subheadline}}
        </mj-text>
      </mj-column>
    </mj-section>
    
    <mj-section background-color="white" padding="40px 30px">
      <mj-column>
        <mj-text font-size="18px" align="center">
          {{offer_text}}
        </mj-text>
        <mj-text align="center" font-size="48px" font-weight="bold" color="{{primary_color}}" padding="20px 0">
          {{discount_code}}
        </mj-text>
        <mj-text align="center" font-size="14px" color="#666666">
          {{expiry_text}}
        </mj-text>
        <mj-button href="{{cta_url}}" font-size="20px" padding="30px">
          {{cta_text}}
        </mj-button>
        <mj-text align="center" font-size="14px" color="#666666">
          {{terms_text}}
        </mj-text>
      </mj-column>
    </mj-section>
    
    <mj-section background-color="#f8f8f8" padding="30px">
      <mj-column>
        <mj-text align="center" font-size="12px" color="#666666">
          {{footer_text}}
        </mj-text>
      </mj-column>
    </mj-section>'''
    
    def _get_announcement_template(self) -> str:
        """Get announcement email template."""
        return '''<mj-section background-color="{{primary_color}}" padding="40px 20px">
      <mj-column>
        <mj-text align="center" color="white" font-size="14px" text-transform="uppercase" letter-spacing="2px">
          {{announcement_label}}
        </mj-text>
        <mj-text align="center" color="white" font-size="28px" font-weight="bold">
          {{headline}}
        </mj-text>
      </mj-column>
    </mj-section>
    
    <mj-section background-color="white" padding="40px 30px">
      <mj-column>
        <mj-image src="{{hero_image}}" alt="{{hero_alt}}" padding="0 0 30px" />
        <mj-text font-size="20px" font-weight="bold">
          {{section_title}}
        </mj-text>
        <mj-text>
          {{body_content}}
        </mj-text>
        <mj-text>
          {{key_features}}
        </mj-text>
        <mj-button href="{{cta_url}}" padding="30px 0">
          {{cta_text}}
        </mj-button>
        <mj-text font-size="14px" color="#666666">
          {{additional_info}}
        </mj-text>
      </mj-column>
    </mj-section>
    
    <mj-section background-color="#f8f8f8" padding="20px">
      <mj-column>
        <mj-text align="center" font-size="12px" color="#666666">
          {{footer_text}}
        </mj-text>
      </mj-column>
    </mj-section>'''
    
    def _get_nurture_template(self) -> str:
        """Get nurture email template."""
        return '''<mj-section background-color="white" padding="40px 30px">
      <mj-column>
        <mj-text font-size="24px" font-weight="bold" color="#333333">
          {{headline}}
        </mj-text>
        <mj-text font-size="16px" color="#666666" padding="10px 0">
          {{subheadline}}
        </mj-text>
      </mj-column>
    </mj-section>
    
    <mj-section background-color="white" padding="0 30px 40px">
      <mj-column>
        <mj-text>
          {{opening_text}}
        </mj-text>
        <mj-text font-size="18px" font-weight="bold" padding-top="20px">
          {{tip_title}}
        </mj-text>
        <mj-text>
          {{tip_content}}
        </mj-text>
        <mj-text font-size="18px" font-weight="bold" padding-top="20px">
          {{resource_title}}
        </mj-text>
        <mj-text>
          {{resource_content}}
        </mj-text>
        <mj-button href="{{cta_url}}" background-color="transparent" color="{{primary_color}}" border="2px solid {{primary_color}}" padding="30px 0">
          {{cta_text}}
        </mj-button>
      </mj-column>
    </mj-section>
    
    <mj-section background-color="{{primary_color}}" padding="30px">
      <mj-column>
        <mj-text align="center" color="white" font-size="16px">
          {{closing_text}}
        </mj-text>
      </mj-column>
    </mj-section>
    
    <mj-section background-color="#f8f8f8" padding="20px">
      <mj-column>
        <mj-text align="center" font-size="12px" color="#666666">
          {{footer_text}}
        </mj-text>
      </mj-column>
    </mj-section>'''
    
    def _get_transactional_template(self) -> str:
        """Get transactional email template (order confirmations, receipts, etc.)."""
        return '''<mj-section background-color="{{primary_color}}" padding="30px 20px">
      <mj-column>
        <mj-text align="center" color="white" font-size="14px" text-transform="uppercase" letter-spacing="2px">
          {{transaction_type}}
        </mj-text>
        <mj-text align="center" color="white" font-size="24px" font-weight="bold">
          {{headline}}
        </mj-text>
        <mj-text align="center" color="white" font-size="14px">
          {{transaction_id}}
        </mj-text>
      </mj-column>
    </mj-section>
    
    <mj-section background-color="white" padding="40px 30px">
      <mj-column>
        <mj-text font-size="16px" color="#333333">
          {{summary_text}}
        </mj-text>
        <mj-divider border-color="#e0e0e0" padding="20px 0" />
        <mj-text font-size="14px" color="#333333">
          {{details_content}}
        </mj-text>
      </mj-column>
    </mj-section>
    
    <mj-section background-color="#f8f8f8" padding="30px">
      <mj-column>
        <mj-text font-size="16px" font-weight="bold" color="#333333">
          Next Steps
        </mj-text>
        <mj-text font-size="14px" color="#666666">
          {{next_steps}}
        </mj-text>
        <mj-button href="{{cta_url}}" padding="20px 0">
          {{cta_text}}
        </mj-button>
      </mj-column>
    </mj-section>
    
    <mj-section background-color="white" padding="20px 30px">
      <mj-column>
        <mj-text font-size="14px" color="#666666">
          {{support_text}}
        </mj-text>
      </mj-column>
    </mj-section>
    
    <mj-section background-color="#333333" padding="20px">
      <mj-column>
        <mj-text align="center" color="#999999" font-size="12px">
          {{footer_text}}
        </mj-text>
      </mj-column>
    </mj-section>'''
    
    def apply_brand(
        self,
        template_name: str,
        brand_data: Dict[str, Any],
        content_data: Dict[str, Any]
    ) -> str:
        """
        Apply brand data and content to a template.
        
        Args:
            template_name: Name of the template to use
            brand_data: Brand colors, fonts, etc.
            content_data: Email content variables
            
        Returns:
            Populated MJML template
        """
        template = self.templates.get(template_name)
        if not template:
            raise ValueError(f"Template not found: {template_name}")
        
        # Get brand values
        primary_color = brand_data.get('primary_color', '#3b82f6')
        font_family = brand_data.get('font_family', 'Arial')
        font_family_url = font_family.replace(' ', '+')
        
        # Build the full MJML
        base = self._get_base_template()
        
        # Replace brand variables
        mjml = base.replace('{{content}}', template.mjml_template)
        mjml = mjml.replace('{{primary_color}}', primary_color)
        mjml = mjml.replace('{{font_family}}', font_family)
        mjml = mjml.replace('{{font_family_url}}', font_family_url)
        
        # Replace content variables
        for key, value in content_data.items():
            mjml = mjml.replace(f'{{{{{key}}}}}', str(value))
        
        # Clean up any remaining placeholders
        mjml = re.sub(r'\{\{\w+\}\}', '', mjml)
        
        return mjml
    
    def mjml_to_html(self, mjml: str) -> str:
        """
        Convert MJML to HTML.
        
        Note: In production, this would call the MJML API or use mjml-python.
        This implementation provides a table-based HTML structure for better
        email client compatibility.
        """
        # Extract body content and background color
        body_match = re.search(r'<mj-body[^>]*background-color="([^"]*)"[^>]*>(.*?)</mj-body>', mjml, re.DOTALL)
        if body_match:
            body_bg = body_match.group(1)
            body_content = body_match.group(2)
        else:
            body_match = re.search(r'<mj-body[^>]*>(.*?)</mj-body>', mjml, re.DOTALL)
            body_content = body_match.group(1) if body_match else mjml
            body_bg = "#f4f4f4"
        
        # Extract font family from head
        font_match = re.search(r'font-family="([^"]+)"', mjml)
        font_family = font_match.group(1) if font_match else "Arial, sans-serif"
        
        # Convert MJML sections to table rows
        def convert_section(match):
            attrs = match.group(1)
            content = match.group(2)
            
            # Extract section attributes
            bg_match = re.search(r'background-color="([^"]+)"', attrs)
            bg_color = bg_match.group(1) if bg_match else "transparent"
            
            padding_match = re.search(r'padding="([^"]+)"', attrs)
            padding = padding_match.group(1) if padding_match else "20px"
            
            return f'''<tr>
<td style="background-color: {bg_color}; padding: {padding};">
<table width="100%" cellpadding="0" cellspacing="0" border="0">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" border="0" style="max-width: 600px; width: 100%;">
{content}
</table>
</td></tr>
</table>
</td>
</tr>'''
        
        html = re.sub(r'<mj-section([^>]*)>(.*?)</mj-section>', convert_section, body_content, flags=re.DOTALL)
        
        # Convert columns
        def convert_column(match):
            attrs = match.group(1)
            content = match.group(2)
            return f'<tr><td style="padding: 0;">{content}</td></tr>'
        
        html = re.sub(r'<mj-column([^>]*)>(.*?)</mj-column>', convert_column, html, flags=re.DOTALL)
        
        # Convert text elements
        def convert_text(match):
            attrs = match.group(1)
            content = match.group(2)
            
            style_parts = ["margin: 0;"]
            
            align_match = re.search(r'align="([^"]+)"', attrs)
            if align_match:
                style_parts.append(f"text-align: {align_match.group(1)}")
            
            color_match = re.search(r'color="([^"]+)"', attrs)
            if color_match:
                style_parts.append(f"color: {color_match.group(1)}")
            
            font_size_match = re.search(r'font-size="([^"]+)"', attrs)
            if font_size_match:
                style_parts.append(f"font-size: {font_size_match.group(1)}")
            
            font_weight_match = re.search(r'font-weight="([^"]+)"', attrs)
            if font_weight_match:
                style_parts.append(f"font-weight: {font_weight_match.group(1)}")
            
            padding_match = re.search(r'padding="([^"]+)"', attrs)
            padding = padding_match.group(1) if padding_match else "10px 0"
            style_parts.append(f"padding: {padding}")
            
            letter_spacing_match = re.search(r'letter-spacing="([^"]+)"', attrs)
            if letter_spacing_match:
                style_parts.append(f"letter-spacing: {letter_spacing_match.group(1)}")
            
            text_transform_match = re.search(r'text-transform="([^"]+)"', attrs)
            if text_transform_match:
                style_parts.append(f"text-transform: {text_transform_match.group(1)}")
            
            style = "; ".join(style_parts)
            return f'<p style="{style}">{content}</p>'
        
        html = re.sub(r'<mj-text([^>]*)>(.*?)</mj-text>', convert_text, html, flags=re.DOTALL)
        
        # Convert buttons
        def convert_button(match):
            attrs = match.group(1)
            content = match.group(2)
            
            href_match = re.search(r'href="([^"]+)"', attrs)
            href = href_match.group(1) if href_match else "#"
            
            bg_match = re.search(r'background-color="([^"]+)"', attrs)
            bg_color = bg_match.group(1) if bg_match else "#3b82f6"
            
            color_match = re.search(r'color="([^"]+)"', attrs)
            text_color = color_match.group(1) if color_match else "white"
            
            border_match = re.search(r'border="([^"]+)"', attrs)
            border = border_match.group(1) if border_match else "none"
            
            padding_match = re.search(r'padding="([^"]+)"', attrs)
            outer_padding = padding_match.group(1) if padding_match else "20px 0"
            
            font_size_match = re.search(r'font-size="([^"]+)"', attrs)
            font_size = font_size_match.group(1) if font_size_match else "16px"
            
            return f'''<table width="100%" cellpadding="0" cellspacing="0" border="0" style="padding: {outer_padding};">
<tr><td align="center">
<a href="{href}" style="display: inline-block; background-color: {bg_color}; color: {text_color}; padding: 12px 24px; text-decoration: none; border-radius: 4px; font-weight: bold; font-size: {font_size}; border: {border};">{content}</a>
</td></tr>
</table>'''
        
        html = re.sub(r'<mj-button([^>]*)>(.*?)</mj-button>', convert_button, html, flags=re.DOTALL)
        
        # Convert images
        def convert_image(match):
            attrs = match.group(1)
            
            src_match = re.search(r'src="([^"]+)"', attrs)
            src = src_match.group(1) if src_match else ""
            
            alt_match = re.search(r'alt="([^"]+)"', attrs)
            alt = alt_match.group(1) if alt_match else ""
            
            padding_match = re.search(r'padding="([^"]+)"', attrs)
            padding = padding_match.group(1) if padding_match else "0"
            
            return f'<img src="{src}" alt="{alt}" style="max-width: 100%; height: auto; display: block; padding: {padding};" />'
        
        html = re.sub(r'<mj-image([^>]*)/?\s*>', convert_image, html)
        
        # Convert dividers
        def convert_divider(match):
            attrs = match.group(1)
            
            border_color_match = re.search(r'border-color="([^"]+)"', attrs)
            border_color = border_color_match.group(1) if border_color_match else "#e0e0e0"
            
            padding_match = re.search(r'padding="([^"]+)"', attrs)
            padding = padding_match.group(1) if padding_match else "10px 0"
            
            return f'<hr style="border: none; border-top: 1px solid {border_color}; margin: 0; padding: {padding};" />'
        
        html = re.sub(r'<mj-divider([^>]*)/?\s*>', convert_divider, html)
        
        # Wrap in email-compatible HTML structure
        full_html = f'''<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="x-apple-disable-message-reformatting">
    <title>Email</title>
    <!--[if mso]>
    <noscript>
        <xml>
            <o:OfficeDocumentSettings>
                <o:PixelsPerInch>96</o:PixelsPerInch>
            </o:OfficeDocumentSettings>
        </xml>
    </noscript>
    <![endif]-->
    <style type="text/css">
        body, table, td, a {{ -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }}
        table, td {{ mso-table-lspace: 0pt; mso-table-rspace: 0pt; }}
        img {{ -ms-interpolation-mode: bicubic; border: 0; height: auto; line-height: 100%; outline: none; text-decoration: none; }}
        body {{ margin: 0 !important; padding: 0 !important; width: 100% !important; }}
        a[x-apple-data-detectors] {{ color: inherit !important; text-decoration: none !important; font-size: inherit !important; font-family: inherit !important; font-weight: inherit !important; line-height: inherit !important; }}
        @media only screen and (max-width: 620px) {{
            .email-container {{ width: 100% !important; max-width: 100% !important; }}
        }}
    </style>
</head>
<body style="margin: 0; padding: 0; background-color: {body_bg}; font-family: {font_family};">
    <center style="width: 100%; background-color: {body_bg};">
        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: {body_bg};">
            {html}
        </table>
    </center>
</body>
</html>'''
        
        return full_html
    
    def html_to_plaintext(self, html: str) -> str:
        """Convert HTML to plain text."""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', html)
        
        # Decode HTML entities (& must be last to avoid double-decoding)
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = text.replace('&amp;', '&')
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    
    def get_available_templates(self) -> List[Dict[str, str]]:
        """Get list of available templates."""
        return [
            {
                "id": key,
                "name": template.name,
                "category": template.category,
                "description": template.description
            }
            for key, template in self.templates.items()
        ]


# Convenience functions
def generate_email(
    template_name: str,
    brand_data: Dict[str, Any],
    content_data: Dict[str, Any],
    subject: str
) -> GeneratedEmail:
    """
    Generate a complete email with all formats.
    
    Args:
        template_name: Template to use
        brand_data: Brand colors, fonts
        content_data: Email content
        subject: Email subject line
        
    Returns:
        GeneratedEmail with MJML, HTML, and plaintext
    """
    system = MJMLTemplateSystem()
    
    # Generate MJML
    mjml = system.apply_brand(template_name, brand_data, content_data)
    
    # Convert to HTML
    html = system.mjml_to_html(mjml)
    
    # Convert to plaintext
    plaintext = system.html_to_plaintext(html)
    
    return GeneratedEmail(
        subject=subject,
        mjml=mjml,
        html=html,
        plaintext=plaintext
    )