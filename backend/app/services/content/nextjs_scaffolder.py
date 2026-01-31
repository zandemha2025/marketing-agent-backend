"""
Next.js Project Scaffolder

Creates complete, deployable Next.js projects with:
- Next.js App Router project structure
- Tailwind CSS integration
- Shadcn/ui components
- Brand DNA styling integration
- SEO optimization
- Deployment configs for Vercel/Netlify
"""
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import json

from .landing_page_generator import LandingPageContent, LandingPageSection, LandingPageType

logger = logging.getLogger(__name__)


@dataclass
class NextJSProject:
    """A complete Next.js project structure."""
    name: str
    files: Dict[str, str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "files": self.files
        }


class NextJSScaffolder:
    """
    Scaffold complete Next.js projects.
    
    Creates:
    - Project structure with App Router
    - Configuration files (package.json, tsconfig, tailwind)
    - Component files with shadcn/ui
    - Brand DNA styling integration
    - Deployment configs
    """
    
    def scaffold_project(
        self,
        project_name: str,
        landing_page: LandingPageContent,
        brand_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Scaffold a complete Next.js project.
        
        Args:
            project_name: Name of the project
            landing_page: Generated landing page content
            brand_context: Brand colors, fonts, etc.
            
        Returns:
            Dictionary of filepath -> file content
        """
        brand_context = brand_context or {}
        brand_colors = brand_context.get("colors", {})
        
        files = {}
        
        # Core configuration files
        files["package.json"] = self._generate_package_json(project_name)
        files["tsconfig.json"] = self._generate_tsconfig()
        files["tailwind.config.ts"] = self.generate_tailwind_config(brand_colors)
        files["next.config.js"] = self._generate_next_config()
        files["postcss.config.js"] = self._generate_postcss_config()
        files[".gitignore"] = self._generate_gitignore()
        files[".env.example"] = self._generate_env_example()
        
        # Lib utilities
        files["lib/utils.ts"] = self._generate_utils()
        
        # App files
        files["app/layout.tsx"] = self.generate_layout(brand_context)
        files["app/globals.css"] = self._generate_globals_css(brand_colors)
        files["app/page.tsx"] = self._generate_page(landing_page)
        
        # UI Components (shadcn-style)
        files["components/ui/button.tsx"] = self._generate_button_component()
        files["components/ui/input.tsx"] = self._generate_input_component()
        files["components/ui/card.tsx"] = self._generate_card_component()
        files["components/ui/accordion.tsx"] = self._generate_accordion_component()
        
        # Section Components
        for section in landing_page.sections:
            component_name = self._get_component_name(section.section_type)
            files[f"components/sections/{component_name}.tsx"] = self.generate_component(
                section, brand_colors
            )
        
        # Main Landing Page Component
        files["components/LandingPage.tsx"] = self._generate_landing_component(
            landing_page, brand_colors
        )
        
        # Deployment configs
        files["vercel.json"] = self._generate_vercel_config()
        files["netlify.toml"] = self._generate_netlify_config()
        
        # Documentation
        files["README.md"] = self._generate_readme(project_name)
        
        return files
    
    def scaffold(
        self,
        project_name: str,
        landing_page_content: Dict[str, Any],
        brand_data: Dict[str, Any]
    ) -> "NextJSProject":
        """
        Scaffold a complete Next.js project (legacy interface).
        
        Args:
            project_name: Name of the project
            landing_page_content: Generated landing page content as dict
            brand_data: Brand colors, fonts, etc.
            
        Returns:
            NextJSProject with all files
        """
        # Convert dict to LandingPageContent if needed
        if isinstance(landing_page_content, dict):
            sections = []
            for s in landing_page_content.get("sections", []):
                sections.append(LandingPageSection(
                    section_type=s.get("type", s.get("section_type", "content")),
                    headline=s.get("title", s.get("headline", "")),
                    subheadline=s.get("subheadline"),
                    content=s.get("content", {}),
                    cta_text=s.get("cta_text"),
                    cta_url=s.get("cta_url"),
                    image_prompt=s.get("image_prompt")
                ))
            
            landing_page = LandingPageContent(
                page_type=LandingPageType(landing_page_content.get("page_type", "product")),
                title=landing_page_content.get("title", "Landing Page"),
                meta_description=landing_page_content.get("seo_description", landing_page_content.get("meta_description", "")),
                og_title=landing_page_content.get("og_title", landing_page_content.get("title", "")),
                og_description=landing_page_content.get("og_description", landing_page_content.get("seo_description", "")),
                sections=sections,
                keywords=landing_page_content.get("keywords", [])
            )
        else:
            landing_page = landing_page_content
        
        files = self.scaffold_project(
            project_name=project_name,
            landing_page=landing_page,
            brand_context={"colors": brand_data}
        )
        
        return NextJSProject(name=project_name, files=files)
    
    def generate_component(
        self,
        section: LandingPageSection,
        brand_colors: Dict[str, Any]
    ) -> str:
        """
        Generate a React component for a section.
        
        Args:
            section: Landing page section
            brand_colors: Brand color palette
            
        Returns:
            TypeScript React component code
        """
        component_name = self._get_component_name(section.section_type)
        primary_color = brand_colors.get("primary_color", "#3b82f6")
        
        # Generate section-specific component
        if section.section_type == "hero":
            return self._generate_hero_component(section, primary_color, component_name)
        elif section.section_type == "features":
            return self._generate_features_component(section, component_name)
        elif section.section_type == "benefits":
            return self._generate_benefits_component(section, component_name)
        elif section.section_type == "testimonials":
            return self._generate_testimonials_component(section, component_name)
        elif section.section_type == "pricing":
            return self._generate_pricing_component(section, primary_color, component_name)
        elif section.section_type == "faq":
            return self._generate_faq_component(section, component_name)
        elif section.section_type == "how_it_works":
            return self._generate_how_it_works_component(section, primary_color, component_name)
        elif section.section_type == "social_proof":
            return self._generate_social_proof_component(section, primary_color, component_name)
        elif section.section_type == "cta":
            return self._generate_cta_component(section, primary_color, component_name)
        elif section.section_type == "countdown":
            return self._generate_countdown_component(section, primary_color, component_name)
        elif section.section_type == "comparison":
            return self._generate_comparison_component(section, primary_color, component_name)
        elif section.section_type == "email_capture":
            return self._generate_email_capture_component(section, primary_color, component_name)
        else:
            return self._generate_generic_component(section, component_name)
    
    def generate_tailwind_config(self, brand_colors: Dict[str, Any]) -> str:
        """
        Generate Tailwind config with brand colors.
        
        Args:
            brand_colors: Brand color palette
            
        Returns:
            Tailwind config TypeScript code
        """
        primary_color = brand_colors.get("primary_color", "#3b82f6")
        secondary_color = brand_colors.get("secondary_color", "#10b981")
        
        return f'''import type {{ Config }} from 'tailwindcss'

const config: Config = {{
  darkMode: ["class"],
  content: [
    './pages/**/*.{{js,ts,jsx,tsx,mdx}}',
    './components/**/*.{{js,ts,jsx,tsx,mdx}}',
    './app/**/*.{{js,ts,jsx,tsx,mdx}}',
  ],
  theme: {{
    extend: {{
      colors: {{
        primary: {{
          DEFAULT: '{primary_color}',
          foreground: '#ffffff',
        }},
        secondary: {{
          DEFAULT: '{secondary_color}',
          foreground: '#ffffff',
        }},
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        card: {{
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        }},
        muted: {{
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        }},
        accent: {{
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        }},
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
      }},
      borderRadius: {{
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      }},
    }},
  }},
  plugins: [require("tailwindcss-animate")],
}}

export default config'''
    
    def generate_layout(self, brand_context: Dict[str, Any]) -> str:
        """
        Generate app/layout.tsx with brand styling.
        
        Args:
            brand_context: Brand colors, fonts, etc.
            
        Returns:
            Layout component TypeScript code
        """
        font_family = brand_context.get("font_family", "Inter")
        # Sanitize font name for import
        font_import_name = font_family.replace(" ", "_")
        
        return f'''import type {{ Metadata }} from 'next'
import {{ {font_import_name} }} from 'next/font/google'
import './globals.css'

const font = {font_import_name}({{ 
  subsets: ['latin'],
  variable: '--font-sans',
}})

export const metadata: Metadata = {{
  title: 'Landing Page',
  description: 'Generated by Marketing Agent Platform',
}}

export default function RootLayout({{
  children,
}}: {{
  children: React.ReactNode
}}) {{
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={{`${{font.variable}} font-sans antialiased`}}>
        {{children}}
      </body>
    </html>
  )
}}'''
    
    def _get_component_name(self, section_type: str) -> str:
        """Convert section type to component name."""
        return "".join(word.title() for word in section_type.split("_")) + "Section"
    
    def _generate_package_json(self, project_name: str) -> str:
        """Generate package.json."""
        return f'''{{
  "name": "{project_name}",
  "version": "0.1.0",
  "private": true,
  "scripts": {{
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  }},
  "dependencies": {{
    "next": "14.1.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "@radix-ui/react-accordion": "^1.1.2",
    "@radix-ui/react-slot": "^1.0.2",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.2.0",
    "tailwindcss-animate": "^1.0.7",
    "lucide-react": "^0.312.0"
  }},
  "devDependencies": {{
    "typescript": "^5.3.0",
    "@types/node": "^20.11.0",
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "autoprefixer": "^10.4.17",
    "postcss": "^8.4.33",
    "tailwindcss": "^3.4.1",
    "eslint": "^8.56.0",
    "eslint-config-next": "14.1.0"
  }}
}}'''
    
    def _generate_tsconfig(self) -> str:
        """Generate tsconfig.json."""
        return '''{
  "compilerOptions": {
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [
      {
        "name": "next"
      }
    ],
    "paths": {
      "@/*": ["./*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}'''
    
    def _generate_next_config(self) -> str:
        """Generate next.config.js."""
        return '''/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  distDir: 'dist',
  images: {
    unoptimized: true,
  },
}

module.exports = nextConfig'''
    
    def _generate_postcss_config(self) -> str:
        """Generate postcss.config.js."""
        return '''module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}'''
    
    def _generate_gitignore(self) -> str:
        """Generate .gitignore."""
        return '''# Dependencies
node_modules
.pnp
.pnp.js

# Testing
coverage

# Next.js
.next/
out/
dist/
build

# Misc
.DS_Store
*.pem

# Debug
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Local env files
.env
.env.local
.env.development.local
.env.test.local
.env.production.local

# Vercel
.vercel

# TypeScript
*.tsbuildinfo
next-env.d.ts
'''
    
    def _generate_env_example(self) -> str:
        """Generate .env.example."""
        return '''# Analytics (optional)
NEXT_PUBLIC_GA_ID=

# API endpoints (optional)
NEXT_PUBLIC_API_URL=
'''
    
    def _generate_utils(self) -> str:
        """Generate lib/utils.ts."""
        return '''import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
'''
    
    def _generate_globals_css(self, brand_colors: Dict[str, Any]) -> str:
        """Generate app/globals.css."""
        primary_color = brand_colors.get("primary_color", "#3b82f6")
        
        return f'''@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {{
  :root {{
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;
    --popover: 0 0% 100%;
    --popover-foreground: 222.2 84% 4.9%;
    --primary: 221.2 83.2% 53.3%;
    --primary-foreground: 210 40% 98%;
    --secondary: 210 40% 96.1%;
    --secondary-foreground: 222.2 47.4% 11.2%;
    --muted: 210 40% 96.1%;
    --muted-foreground: 215.4 16.3% 46.9%;
    --accent: 210 40% 96.1%;
    --accent-foreground: 222.2 47.4% 11.2%;
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 210 40% 98%;
    --border: 214.3 31.8% 91.4%;
    --input: 214.3 31.8% 91.4%;
    --ring: 221.2 83.2% 53.3%;
    --radius: 0.5rem;
  }}

  .dark {{
    --background: 222.2 84% 4.9%;
    --foreground: 210 40% 98%;
    --card: 222.2 84% 4.9%;
    --card-foreground: 210 40% 98%;
    --popover: 222.2 84% 4.9%;
    --popover-foreground: 210 40% 98%;
    --primary: 217.2 91.2% 59.8%;
    --primary-foreground: 222.2 47.4% 11.2%;
    --secondary: 217.2 32.6% 17.5%;
    --secondary-foreground: 210 40% 98%;
    --muted: 217.2 32.6% 17.5%;
    --muted-foreground: 215 20.2% 65.1%;
    --accent: 217.2 32.6% 17.5%;
    --accent-foreground: 210 40% 98%;
    --destructive: 0 62.8% 30.6%;
    --destructive-foreground: 210 40% 98%;
    --border: 217.2 32.6% 17.5%;
    --input: 217.2 32.6% 17.5%;
    --ring: 224.3 76.3% 48%;
  }}
}}

@layer base {{
  * {{
    @apply border-border;
  }}
  body {{
    @apply bg-background text-foreground;
  }}
}}

html {{
  scroll-behavior: smooth;
}}
'''
    
    def _generate_page(self, landing_page: LandingPageContent) -> str:
        """Generate app/page.tsx."""
        return f'''import {{ Metadata }} from 'next'
import LandingPage from '@/components/LandingPage'

export const metadata: Metadata = {{
  title: '{landing_page.title}',
  description: '{landing_page.meta_description}',
  openGraph: {{
    title: '{landing_page.og_title}',
    description: '{landing_page.og_description}',
    type: 'website',
  }},
  twitter: {{
    card: 'summary_large_image',
    title: '{landing_page.og_title}',
    description: '{landing_page.og_description}',
  }},
  keywords: {json.dumps(landing_page.keywords)},
}}

export default function Home() {{
  return <LandingPage />
}}'''
    
    def _generate_landing_component(
        self,
        landing_page: LandingPageContent,
        brand_colors: Dict[str, Any]
    ) -> str:
        """Generate the main LandingPage component."""
        
        # Build imports
        imports = ['"use client"', '', 'import React from "react"']
        for section in landing_page.sections:
            component_name = self._get_component_name(section.section_type)
            imports.append(f'import {component_name} from "@/components/sections/{component_name}"')
        
        # Build component body
        section_renders = "\n      ".join([
            f"<{self._get_component_name(section.section_type)} />"
            for section in landing_page.sections
        ])
        
        return f'''{chr(10).join(imports)}

export default function LandingPage() {{
  return (
    <div className="min-h-screen bg-background">
      {section_renders}
    </div>
  )
}}
'''
    
    def _generate_button_component(self) -> str:
        """Generate shadcn-style Button component."""
        return '''import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }
'''
    
    def _generate_input_component(self) -> str:
        """Generate shadcn-style Input component."""
        return '''import * as React from "react"
import { cn } from "@/lib/utils"

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Input.displayName = "Input"

export { Input }
'''
    
    def _generate_card_component(self) -> str:
        """Generate shadcn-style Card component."""
        return '''import * as React from "react"
import { cn } from "@/lib/utils"

const Card = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "rounded-lg border bg-card text-card-foreground shadow-sm",
      className
    )}
    {...props}
  />
))
Card.displayName = "Card"

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex flex-col space-y-1.5 p-6", className)}
    {...props}
  />
))
CardHeader.displayName = "CardHeader"

const CardTitle = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn(
      "text-2xl font-semibold leading-none tracking-tight",
      className
    )}
    {...props}
  />
))
CardTitle.displayName = "CardTitle"

const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn("text-sm text-muted-foreground", className)}
    {...props}
  />
))
CardDescription.displayName = "CardDescription"

const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("p-6 pt-0", className)} {...props} />
))
CardContent.displayName = "CardContent"

const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex items-center p-6 pt-0", className)}
    {...props}
  />
))
CardFooter.displayName = "CardFooter"

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent }
'''
    
    def _generate_accordion_component(self) -> str:
        """Generate shadcn-style Accordion component."""
        return '''import * as React from "react"
import * as AccordionPrimitive from "@radix-ui/react-accordion"
import { ChevronDown } from "lucide-react"
import { cn } from "@/lib/utils"

const Accordion = AccordionPrimitive.Root

const AccordionItem = React.forwardRef<
  React.ElementRef<typeof AccordionPrimitive.Item>,
  React.ComponentPropsWithoutRef<typeof AccordionPrimitive.Item>
>(({ className, ...props }, ref) => (
  <AccordionPrimitive.Item
    ref={ref}
    className={cn("border-b", className)}
    {...props}
  />
))
AccordionItem.displayName = "AccordionItem"

const AccordionTrigger = React.forwardRef<
  React.ElementRef<typeof AccordionPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof AccordionPrimitive.Trigger>
>(({ className, children, ...props }, ref) => (
  <AccordionPrimitive.Header className="flex">
    <AccordionPrimitive.Trigger
      ref={ref}
      className={cn(
        "flex flex-1 items-center justify-between py-4 font-medium transition-all hover:underline [&[data-state=open]>svg]:rotate-180",
        className
      )}
      {...props}
    >
      {children}
      <ChevronDown className="h-4 w-4 shrink-0 transition-transform duration-200" />
    </AccordionPrimitive.Trigger>
  </AccordionPrimitive.Header>
))
AccordionTrigger.displayName = AccordionPrimitive.Trigger.displayName

const AccordionContent = React.forwardRef<
  React.ElementRef<typeof AccordionPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof AccordionPrimitive.Content>
>(({ className, children, ...props }, ref) => (
  <AccordionPrimitive.Content
    ref={ref}
    className="overflow-hidden text-sm transition-all data-[state=closed]:animate-accordion-up data-[state=open]:animate-accordion-down"
    {...props}
  >
    <div className={cn("pb-4 pt-0", className)}>{children}</div>
  </AccordionPrimitive.Content>
))

AccordionContent.displayName = AccordionPrimitive.Content.displayName

export { Accordion, AccordionItem, AccordionTrigger, AccordionContent }
'''
    
    # Section component generators
    def _generate_hero_component(self, section: LandingPageSection, primary_color: str, component_name: str) -> str:
        """Generate Hero section component."""
        content = section.content or {}
        return f'''"use client"

import React from "react"
import {{ Button }} from "@/components/ui/button"
import {{ ArrowRight }} from "lucide-react"

export default function {component_name}() {{
  return (
    <section className="relative bg-gradient-to-br from-gray-900 to-gray-800 text-white py-24 px-4 overflow-hidden">
      <div className="absolute inset-0 bg-[url('/hero-pattern.svg')] opacity-10" />
      <div className="relative max-w-5xl mx-auto text-center">
        <h1 className="text-5xl md:text-6xl font-bold mb-6 leading-tight">
          {section.headline}
        </h1>
        <p className="text-xl md:text-2xl text-gray-300 mb-10 max-w-3xl mx-auto">
          {section.subheadline or ''}
        </p>
        <Button 
          size="lg" 
          className="bg-primary hover:bg-primary/90 text-white px-8 py-6 text-lg"
          asChild
        >
          <a href="{section.cta_url or '#'}">
            {section.cta_text or 'Get Started'}
            <ArrowRight className="ml-2 h-5 w-5" />
          </a>
        </Button>
        {f'<p className="mt-4 text-sm text-gray-400">{content.get("cta_subtext", "")}</p>' if content.get("cta_subtext") else ''}
      </div>
    </section>
  )
}}
'''
    
    def _generate_features_component(self, section: LandingPageSection, component_name: str) -> str:
        """Generate Features section component."""
        features = section.content.get("features", [])
        features_json = json.dumps(features, indent=2)
        
        return f'''"use client"

import React from "react"
import {{ Card, CardContent }} from "@/components/ui/card"

const features = {features_json}

export default function {component_name}() {{
  return (
    <section className="py-24 px-4 bg-muted/50">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-bold mb-4">{section.headline}</h2>
          <p className="text-xl text-muted-foreground">{section.subheadline or ''}</p>
        </div>
        <div className="grid md:grid-cols-3 gap-8">
          {{features.map((feature, index) => (
            <Card key={{index}} className="hover:shadow-lg transition-shadow">
              <CardContent className="p-8">
                <div className="text-4xl mb-4">{{feature.icon}}</div>
                <h3 className="text-xl font-semibold mb-3">{{feature.title}}</h3>
                <p className="text-muted-foreground">{{feature.description}}</p>
              </CardContent>
            </Card>
          ))}}
        </div>
      </div>
    </section>
  )
}}
'''
    
    def _generate_benefits_component(self, section: LandingPageSection, component_name: str) -> str:
        """Generate Benefits section component."""
        benefits = section.content.get("benefits", [])
        benefits_json = json.dumps(benefits, indent=2)
        
        return f'''"use client"

import React from "react"
import {{ Check }} from "lucide-react"

const benefits = {benefits_json}

export default function {component_name}() {{
  return (
    <section className="py-24 px-4 bg-background">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-bold mb-4">{section.headline}</h2>
          <p className="text-xl text-muted-foreground">{section.subheadline or ''}</p>
        </div>
        <div className="space-y-6">
          {{benefits.map((benefit, index) => (
            <div key={{index}} className="flex items-start gap-4">
              <div className="flex-shrink-0 w-8 h-8 bg-primary rounded-full flex items-center justify-center text-white">
                <Check className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-lg font-semibold mb-1">{{benefit.title}}</h3>
                <p className="text-muted-foreground">{{benefit.description}}</p>
              </div>
            </div>
          ))}}
        </div>
      </div>
    </section>
  )
}}
'''
    
    def _generate_testimonials_component(self, section: LandingPageSection, component_name: str) -> str:
        """Generate Testimonials section component."""
        testimonials = section.content.get("testimonials", [])
        testimonials_json = json.dumps(testimonials, indent=2)
        
        return f'''"use client"

import React from "react"
import {{ Card, CardContent }} from "@/components/ui/card"
import {{ Star }} from "lucide-react"

const testimonials = {testimonials_json}

export default function {component_name}() {{
  return (
    <section className="py-24 px-4 bg-muted/50">
      <div className="max-w-6xl mx-auto">
        <h2 className="text-4xl font-bold text-center mb-16">{section.headline}</h2>
        <div className="grid md:grid-cols-3 gap-8">
          {{testimonials.map((testimonial, index) => (
            <Card key={{index}} className="bg-background">
              <CardContent className="p-8">
                <div className="flex gap-1 mb-4">
                  {{[...Array(5)].map((_, i) => (
                    <Star key={{i}} className="h-5 w-5 fill-yellow-400 text-yellow-400" />
                  ))}}
                </div>
                <p className="text-foreground mb-6">"{{testimonial.quote}}"</p>
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-muted rounded-full" />
                  <div>
                    <p className="font-semibold">{{testimonial.author}}</p>
                    <p className="text-sm text-muted-foreground">{{testimonial.title}}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}}
        </div>
      </div>
    </section>
  )
}}
'''
    
    def _generate_pricing_component(self, section: LandingPageSection, primary_color: str, component_name: str) -> str:
        """Generate Pricing section component."""
        tiers = section.content.get("tiers", [])
        tiers_json = json.dumps(tiers, indent=2)
        
        return f'''"use client"

import React from "react"
import {{ Button }} from "@/components/ui/button"
import {{ Card, CardContent, CardHeader, CardTitle, CardDescription }} from "@/components/ui/card"
import {{ Check }} from "lucide-react"
import {{ cn }} from "@/lib/utils"

const tiers = {tiers_json}

export default function {component_name}() {{
  return (
    <section className="py-24 px-4 bg-background">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-bold mb-4">{section.headline}</h2>
          <p className="text-xl text-muted-foreground">{section.subheadline or ''}</p>
        </div>
        <div className="grid md:grid-cols-3 gap-8">
          {{tiers.map((tier, index) => (
            <Card 
              key={{index}} 
              className={{cn(
                "relative",
                tier.highlighted && "border-2 border-primary shadow-lg"
              )}}
            >
              {{tier.highlighted && (
                <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-primary text-white px-4 py-1 rounded-full text-sm font-medium">
                  Most Popular
                </div>
              )}}
              <CardHeader>
                <CardTitle>{{tier.name}}</CardTitle>
                <CardDescription>{{tier.description}}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-4xl font-bold mb-6">
                  {{tier.price}}
                  <span className="text-lg text-muted-foreground">{{tier.period}}</span>
                </div>
                <ul className="space-y-3 mb-8">
                  {{tier.features.map((feature, i) => (
                    <li key={{i}} className="flex items-center gap-2">
                      <Check className="h-5 w-5 text-primary" />
                      {{feature}}
                    </li>
                  ))}}
                </ul>
                <Button 
                  className="w-full" 
                  variant={{tier.highlighted ? "default" : "outline"}}
                  asChild
                >
                  <a href={{tier.cta_url || "#"}}>{{tier.cta_text}}</a>
                </Button>
              </CardContent>
            </Card>
          ))}}
        </div>
      </div>
    </section>
  )
}}
'''
    
    def _generate_faq_component(self, section: LandingPageSection, component_name: str) -> str:
        """Generate FAQ section component."""
        questions = section.content.get("questions", [])
        questions_json = json.dumps(questions, indent=2)
        
        return f'''"use client"

import React from "react"
import {{
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
}} from "@/components/ui/accordion"

const questions = {questions_json}

export default function {component_name}() {{
  return (
    <section className="py-24 px-4 bg-muted/50">
      <div className="max-w-3xl mx-auto">
        <h2 className="text-4xl font-bold text-center mb-12">{section.headline}</h2>
        <Accordion type="single" collapsible className="w-full">
          {{questions.map((item, index) => (
            <AccordionItem key={{index}} value={{`item-${{index}}`}}>
              <AccordionTrigger className="text-left">
                {{item.question}}
              </AccordionTrigger>
              <AccordionContent>
                {{item.answer}}
              </AccordionContent>
            </AccordionItem>
          ))}}
        </Accordion>
      </div>
    </section>
  )
}}
'''
    
    def _generate_how_it_works_component(self, section: LandingPageSection, primary_color: str, component_name: str) -> str:
        """Generate How It Works section component."""
        steps = section.content.get("steps", [])
        steps_json = json.dumps(steps, indent=2)
        
        return f'''"use client"

import React from "react"

const steps = {steps_json}

export default function {component_name}() {{
  return (
    <section className="py-24 px-4 bg-background">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-bold mb-4">{section.headline}</h2>
          <p className="text-xl text-muted-foreground">{section.subheadline or ''}</p>
        </div>
        <div className="grid md:grid-cols-{{steps.length}} gap-8">
          {{steps.map((step, index) => (
            <div key={{index}} className="text-center">
              <div className="w-12 h-12 bg-primary text-white rounded-full flex items-center justify-center text-xl font-bold mx-auto mb-4">
                {{index + 1}}
              </div>
              <h3 className="text-xl font-semibold mb-2">{{step.title}}</h3>
              <p className="text-muted-foreground">{{step.description}}</p>
            </div>
          ))}}
        </div>
      </div>
    </section>
  )
}}
'''
    
    def _generate_social_proof_component(self, section: LandingPageSection, primary_color: str, component_name: str) -> str:
        """Generate Social Proof section component."""
        logos = section.content.get("logos", [])
        stats = section.content.get("stats", [])
        logos_json = json.dumps(logos, indent=2)
        stats_json = json.dumps(stats, indent=2)
        
        return f'''"use client"

import React from "react"

const logos = {logos_json}
const stats = {stats_json}

export default function {component_name}() {{
  return (
    <section className="py-16 px-4 bg-muted/50">
      <div className="max-w-6xl mx-auto">
        <h2 className="text-2xl font-bold text-center mb-8">{section.headline}</h2>
        {{logos.length > 0 && (
          <div className="flex flex-wrap justify-center gap-12 mb-12">
            {{logos.map((logo, index) => (
              <div key={{index}} className="text-muted-foreground text-lg font-semibold">
                {{logo}}
              </div>
            ))}}
          </div>
        )}}
        {{stats.length > 0 && (
          <div className="grid md:grid-cols-{{stats.length}} gap-8">
            {{stats.map((stat, index) => (
              <div key={{index}} className="text-center">
                <div className="text-4xl font-bold text-primary">{{stat.value}}</div>
                <div className="text-muted-foreground">{{stat.label}}</div>
              </div>
            ))}}
          </div>
        )}}
      </div>
    </section>
  )
}}
'''
    
    def _generate_cta_component(self, section: LandingPageSection, primary_color: str, component_name: str) -> str:
        """Generate CTA section component."""
        content = section.content or {}
        return f'''"use client"

import React from "react"
import {{ Button }} from "@/components/ui/button"

export default function {component_name}() {{
  return (
    <section className="py-24 px-4 bg-primary">
      <div className="max-w-4xl mx-auto text-center text-white">
        <h2 className="text-4xl md:text-5xl font-bold mb-6">
          {section.headline}
        </h2>
        <p className="text-xl mb-10 opacity-90">
          {section.subheadline or ''}
        </p>
        <Button 
          size="lg" 
          variant="secondary"
          className="bg-white text-primary hover:bg-gray-100 px-8 py-6 text-lg"
          asChild
        >
          <a href="{section.cta_url or '#'}">{section.cta_text or 'Get Started'}</a>
        </Button>
        {f'<p className="mt-6 text-sm opacity-75">{content.get("guarantee_text", "")}</p>' if content.get("guarantee_text") else ''}
      </div>
    </section>
  )
}}
'''
    
    def _generate_countdown_component(self, section: LandingPageSection, primary_color: str, component_name: str) -> str:
        """Generate Countdown section component."""
        return f'''"use client"

import React, {{ useState, useEffect }} from "react"
import {{ Button }} from "@/components/ui/button"

export default function {component_name}() {{
  const [timeLeft, setTimeLeft] = useState({{
    days: 0,
    hours: 0,
    minutes: 0,
    seconds: 0,
  }})

  useEffect(() => {{
    const targetDate = new Date("{section.content.get('event_date', '2024-12-31T00:00:00Z')}")
    
    const timer = setInterval(() => {{
      const now = new Date()
      const difference = targetDate.getTime() - now.getTime()
      
      if (difference > 0) {{
        setTimeLeft({{
          days: Math.floor(difference / (1000 * 60 * 60 * 24)),
          hours: Math.floor((difference / (1000 * 60 * 60)) % 24),
          minutes: Math.floor((difference / 1000 / 60) % 60),
          seconds: Math.floor((difference / 1000) % 60),
        }})
      }}
    }}, 1000)

    return () => clearInterval(timer)
  }}, [])

  return (
    <section className="py-16 px-4 bg-gray-900 text-white">
      <div className="max-w-4xl mx-auto text-center">
        <h2 className="text-3xl font-bold mb-4">{section.headline}</h2>
        <p className="text-xl mb-8 opacity-90">{section.subheadline or ''}</p>
        <div className="flex justify-center gap-8 mb-8">
          <div className="text-center">
            <div className="text-5xl font-bold">{{String(timeLeft.days).padStart(2, '0')}}</div>
            <div className="text-sm opacity-75">Days</div>
          </div>
          <div className="text-center">
            <div className="text-5xl font-bold">{{String(timeLeft.hours).padStart(2, '0')}}</div>
            <div className="text-sm opacity-75">Hours</div>
          </div>
          <div className="text-center">
            <div className="text-5xl font-bold">{{String(timeLeft.minutes).padStart(2, '0')}}</div>
            <div className="text-sm opacity-75">Minutes</div>
          </div>
          <div className="text-center">
            <div className="text-5xl font-bold">{{String(timeLeft.seconds).padStart(2, '0')}}</div>
            <div className="text-sm opacity-75">Seconds</div>
          </div>
        </div>
        <Button 
          size="lg" 
          className="bg-primary hover:bg-primary/90 text-white px-8 py-6 text-lg"
          asChild
        >
          <a href="{section.cta_url or '#'}">{section.cta_text or 'Register Now'}</a>
        </Button>
      </div>
    </section>
  )
}}
'''
    
    def _generate_comparison_component(self, section: LandingPageSection, primary_color: str, component_name: str) -> str:
        """Generate Comparison section component."""
        comparison = section.content.get("comparison", {})
        comparison_json = json.dumps(comparison, indent=2)
        
        return f'''"use client"

import React from "react"
import {{ Check, X }} from "lucide-react"

const comparison = {comparison_json}

export default function {component_name}() {{
  const renderValue = (value: string) => {{
    if (value === "✓") return <Check className="h-5 w-5 text-green-500 mx-auto" />
    if (value === "—" || value === "✗") return <X className="h-5 w-5 text-gray-400 mx-auto" />
    return value
  }}

  return (
    <section className="py-24 px-4 bg-background">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-12">
          <h2 className="text-4xl font-bold mb-4">{section.headline}</h2>
          <p className="text-xl text-muted-foreground">{section.subheadline or ''}</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-muted">
                <th className="p-4 text-left">Feature</th>
                <th className="p-4 text-center bg-primary/10 font-bold">
                  {{comparison.our_product?.name}}
                </th>
                {{comparison.competitors?.map((comp, i) => (
                  <th key={{i}} className="p-4 text-center">{{comp.name}}</th>
                ))}}
              </tr>
            </thead>
            <tbody>
              {{comparison.features?.map((feature, i) => (
                <tr key={{i}}>
                  <td className="p-4 border-t">{{feature.name}}</td>
                  <td className="p-4 border-t text-center bg-primary/5">
                    {{renderValue(feature.us)}}
                  </td>
                  {{comparison.competitors?.map((comp, j) => (
                    <td key={{j}} className="p-4 border-t text-center">
                      {{renderValue(feature[comp.key])}}
                    </td>
                  ))}}
                </tr>
              ))}}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}}
'''
    
    def _generate_email_capture_component(self, section: LandingPageSection, primary_color: str, component_name: str) -> str:
        """Generate Email Capture section component."""
        content = section.content or {}
        return f'''"use client"

import React, {{ useState }} from "react"
import {{ Button }} from "@/components/ui/button"
import {{ Input }} from "@/components/ui/input"

export default function {component_name}() {{
  const [email, setEmail] = useState("")
  const [submitted, setSubmitted] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {{
    e.preventDefault()
    // Handle form submission
    console.log("Email submitted:", email)
    setSubmitted(true)
  }}

  return (
    <section className="py-24 px-4 bg-gradient-to-br from-primary to-secondary text-white">
      <div className="max-w-2xl mx-auto text-center">
        <h2 className="text-4xl font-bold mb-4">{section.headline}</h2>
        <p className="text-xl mb-8 opacity-90">{section.subheadline or ''}</p>
        {{submitted ? (
          <div className="bg-white/20 rounded-lg p-6">
            <p className="text-xl font-semibold">Thank you for subscribing!</p>
            <p className="opacity-90">We'll be in touch soon.</p>
          </div>
        ) : (
          <form onSubmit={{handleSubmit}} className="flex flex-col sm:flex-row gap-4 max-w-md mx-auto">
            <Input
              type="email"
              placeholder="Enter your email"
              value={{email}}
              onChange={{(e) => setEmail(e.target.value)}}
              className="flex-1 bg-white text-gray-900"
              required
            />
            <Button 
              type="submit"
              variant="secondary"
              className="bg-white text-primary hover:bg-gray-100"
            >
              {section.cta_text or 'Subscribe'}
            </Button>
          </form>
        )}}
        {f'<p className="mt-4 text-sm opacity-75">{content.get("privacy_note", "")}</p>' if content.get("privacy_note") else ''}
      </div>
    </section>
  )
}}
'''
    
    def _generate_generic_component(self, section: LandingPageSection, component_name: str) -> str:
        """Generate a generic section component."""
        return f'''"use client"

import React from "react"

export default function {component_name}() {{
  return (
    <section className="py-24 px-4">
      <div className="max-w-4xl mx-auto">
        <h2 className="text-4xl font-bold mb-4">{section.headline}</h2>
        <p className="text-xl text-muted-foreground">{section.subheadline or ''}</p>
      </div>
    </section>
  )
}}
'''
    
    def _generate_vercel_config(self) -> str:
        """Generate Vercel deployment config."""
        return '''{
  "version": 2,
  "builds": [
    {
      "src": "package.json",
      "use": "@vercel/next"
    }
  ]
}'''
    
    def _generate_netlify_config(self) -> str:
        """Generate Netlify deployment config."""
        return '''[build]
  command = "npm run build"
  publish = "dist"

[build.environment]
  NODE_VERSION = "18"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
'''
    
    def _generate_readme(self, project_name: str) -> str:
        """Generate README.md."""
        return f'''# {project_name}

Generated by Marketing Agent Platform

## Getting Started

First, install dependencies:

```bash
npm install
```

Then, run the development server:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

## Build for Production

```bash
npm run build
```

## Deploy

### Vercel

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new)

### Netlify

[![Deploy to Netlify](https://www.netlify.com/img/deploy/button.svg)](https://app.netlify.com/start/deploy?repository=)

## Project Structure

```
├── app/                  # Next.js App Router pages
│   ├── layout.tsx       # Root layout
│   ├── page.tsx         # Home page
│   └── globals.css      # Global styles
├── components/          # React components
│   ├── ui/              # UI primitives (shadcn-style)
│   ├── sections/        # Landing page sections
│   └── LandingPage.tsx  # Main landing page
├── lib/                 # Utility functions
│   └── utils.ts         # cn() helper
├── public/              # Static assets
└── dist/                # Build output
```

## Customization

- Edit `tailwind.config.ts` to customize colors and fonts
- Edit components in `components/sections/` to modify sections
- Edit `app/globals.css` for global style changes

## Tech Stack

- [Next.js 14](https://nextjs.org/) - React framework
- [Tailwind CSS](https://tailwindcss.com/) - Utility-first CSS
- [shadcn/ui](https://ui.shadcn.com/) - UI components
- [Lucide React](https://lucide.dev/) - Icons
'''


# Convenience function
def scaffold_nextjs_project(
    project_name: str,
    landing_page_content: Any,
    brand_data: Dict[str, Any]
) -> NextJSProject:
    """Scaffold a Next.js project."""
    scaffolder = NextJSScaffolder()
    return scaffolder.scaffold(project_name, landing_page_content, brand_data)
