# UI Guidelines and Component Documentation

> **Developer Note**: This document follows the [Developer Documentation Guidelines](./developer_documentation_guidelines.md). When implementing or modifying UI components, please maintain documentation according to these standards.

## Overview

This document provides guidelines and documentation for the UI components used in the Grey Literature Search App. Following these guidelines will ensure consistency across all feature slices and make development more efficient.

## Table of Contents

1. [Design Principles](#design-principles)
2. [Color System](#color-system)
3. [Typography](#typography)
4. [Shared Component Library](#shared-component-library)
5. [Feature-Specific Components](#feature-specific-components)
6. [Layout Guidelines](#layout-guidelines)
7. [Form Elements](#form-elements)
8. [Best Practices](#best-practices)
9. [VSA UI Implementation](#vsa-ui-implementation)

## Design Principles

The UI design follows these core principles:

- **Consistency**: Use the same components, patterns, and styles throughout all feature slices
- **Simplicity**: Keep interfaces clean and focused on the task at hand
- **Accessibility**: Ensure all components are accessible to all users
- **Responsiveness**: Design for all screen sizes and devices
- **Feature Autonomy**: Allow feature-specific UI components while maintaining visual consistency

## Color System

The application uses a consistent color palette based on Tailwind CSS:

- **Primary**: Blue (`blue-600`) - Used for primary actions, links, and emphasis
- **Secondary**: Gray (`gray-200`) - Used for secondary actions and UI elements
- **Background**: White/Light Gray gradient - Used for page backgrounds
- **Text**: Dark Gray (`gray-900`) for headings, Medium Gray (`gray-700`) for body text
- **Accent**: Various blues for highlights and focus states
- **Error**: Red (`red-600`) for error states and validation messages
- **Success**: Green (`green-600`) for success states and confirmations

## Typography

Typography follows a hierarchical system:

- **Headings**:
  - H1: `text-4xl md:text-5xl font-bold text-gray-900`
  - H2: `text-3xl font-bold text-gray-900`
  - H3: `text-xl font-semibold text-gray-900`
  
- **Body Text**:
  - Regular: `text-base text-gray-700`
  - Small: `text-sm text-gray-600`
  
- **Labels and Form Elements**:
  - Labels: `text-sm font-medium text-gray-700`
  - Placeholder: `text-gray-500`

## Shared Component Library

The application uses a shared component library built with Tailwind CSS. All shared components are located in `src/shared/ui/`.

### Core Components

#### Button

The Button component (`src/shared/ui/button.tsx`) is used for all interactive actions across features.

**Variants**:
- `default`: Primary blue button
- `secondary`: Gray button for secondary actions
- `outline`: Outlined button with transparent background
- `destructive`: Red button for destructive actions
- `ghost`: Text-only button with hover state
- `link`: Text link style

**Sizes**:
- `default`: Standard size
- `sm`: Small size
- `lg`: Large size
- `icon`: Square button for icons

**Usage Example**:
```tsx
import { Button } from '@/shared/ui';

// Primary button
<Button>Submit</Button>

// Secondary button
<Button variant="secondary">Cancel</Button>

// Large primary button
<Button size="lg" variant="default">Create Account</Button>

// Outline button with icon
<Button variant="outline">
  <Icon className="mr-2 h-4 w-4" />
  Settings
</Button>
```

#### Input

The Input component (`src/shared/ui/input.tsx`) is used for all text input fields.

**Features**:
- Support for labels
- Error state handling
- Helper text
- Start and end icons
- Loading state

**Usage Example**:
```tsx
import { Input } from '@/shared/ui';

// Basic input
<Input 
  id="email"
  type="email"
  placeholder="Enter your email"
  required
/>

// Input with label and error
<Input
  id="password"
  type="password"
  label="Password"
  error="Password must be at least 8 characters"
  required
/>
```

#### Label

The Label component (`src/shared/ui/label.tsx`) is used for form labels.

**Usage Example**:
```tsx
import { Label } from '@/shared/ui';

<Label htmlFor="email" className="text-gray-700 font-medium">
  Email Address
  {required && <span className="text-red-500 ml-1">*</span>}
</Label>
```

### Layout Components

#### Card

The Card component is used for containing related content.

**Usage Example**:
```tsx
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/shared/ui';

<Card>
  <CardHeader>
    <CardTitle>Card Title</CardTitle>
    <CardDescription>Card description text</CardDescription>
  </CardHeader>
  <CardContent>
    <p>Card content goes here</p>
  </CardContent>
  <CardFooter>
    <Button>Action</Button>
  </CardFooter>
</Card>
```

## Feature-Specific Components

In the Vertical Slice Architecture, features can define their own UI components that are specific to their domain. These components should:

1. Be located in the feature's directory: `src/features/feature-name/components/`
2. Follow the same design principles and styling conventions as shared components
3. Be documented in the feature's `UI-COMPONENTS.md` file

### Example: Search Strategy Builder Components

The Search Strategy Builder feature might define these specialized components:

- `ConceptGroup`: For grouping related search terms
- `DomainSelector`: For selecting trusted domains
- `QueryPreview`: For previewing generated search strings

These components would be documented in `src/features/search-strategy/docs/UI-COMPONENTS.md`.

## Layout Guidelines

### Page Structure

Pages should follow this general structure:

1. **Header**: Contains navigation and user actions
2. **Main Content**: Primary content area
3. **Footer**: Contains secondary information and links

### Spacing

Use Tailwind's spacing utilities consistently:

- `space-y-4` for vertical spacing between elements
- `space-x-4` for horizontal spacing between elements
- `p-4` to `p-8` for padding within containers
- `m-4` to `m-8` for margins around containers

### Responsive Design

- Use Tailwind's responsive prefixes (`sm:`, `md:`, `lg:`, `xl:`)
- Design mobile-first, then add breakpoints for larger screens
- Test all interfaces on multiple screen sizes

## Form Elements

### Form Structure

Forms should follow this structure:

```tsx
<form className="space-y-6">
  <div className="space-y-4">
    {/* Form fields go here */}
  </div>
  
  {/* Error message container */}
  {error && (
    <div className="p-3 bg-red-50 border border-red-200 rounded-md">
      <p className="text-sm text-red-600">{error}</p>
    </div>
  )}
  
  {/* Form actions */}
  <Button type="submit" className="w-full">Submit</Button>
</form>
```

### Validation

- Use inline validation where possible
- Show error messages below the relevant field
- Use red color (`text-red-600`, `border-red-500`) for error states

## Best Practices

1. **Import Shared Components from UI Library**:
   Always import shared components from the shared UI library:
   ```tsx
   // Correct
   import { Button, Input } from '@/shared/ui';
   
   // Incorrect
   import { Button } from '../Button/Button';
   ```

2. **Feature-Specific Components**:
   Import feature-specific components from the feature's components directory:
   ```tsx
   // For components specific to the Search Strategy feature
   import { ConceptGroup } from '@/features/search-strategy/components';
   ```

3. **Consistent Styling**:
   Use the predefined Tailwind classes and avoid custom CSS where possible.

4. **Component Props**:
   Use the defined props for components and avoid overriding styles with className unless necessary.

5. **Responsive Design**:
   Always consider mobile views and use responsive classes.

6. **Accessibility**:
   Ensure all interactive elements have proper ARIA attributes and keyboard navigation.

7. **Testing UI Components**:
   When adding new UI components, consider adding them to Storybook for documentation and testing.

## VSA UI Implementation

In the Vertical Slice Architecture, UI components are organized as follows:

### Shared UI Components

Shared UI components are located in `src/shared/ui/` and are available to all features. These include:

- Basic form elements (Button, Input, Select, Checkbox, etc.)
- Layout components (Card, Container, Grid, etc.)
- Feedback components (Alert, Toast, Modal, etc.)
- Navigation components (Tabs, Breadcrumbs, etc.)

### Feature-Specific UI Components

Each feature can define its own UI components that are specific to its domain:

```
src/
  features/
    search-strategy/
      components/           # UI components specific to Search Strategy
        ConceptGroup.tsx
        DomainSelector.tsx
        QueryPreview.tsx
      docs/
        UI-COMPONENTS.md    # Documentation for these components
```

### Component Documentation

For shared UI components:
- Document in this UI Guidelines document
- Include in Storybook

For feature-specific components:
- Document in the feature's `UI-COMPONENTS.md` file
- Include in the feature's Storybook stories

### Component Ownership

- **Shared UI Team**: Responsible for shared UI components
- **Feature Teams**: Responsible for feature-specific UI components

## Adding New Components

### Adding New Shared Components

When adding new components to the shared UI library:

1. Create the component in `src/shared/ui/`
2. Export it from `src/shared/ui/index.ts`
3. Document the component in this guide
4. Add a Storybook story for the component

### Adding New Feature-Specific Components

When adding new components to a feature:

1. Create the component in `src/features/feature-name/components/`
2. Export it from `src/features/feature-name/components/index.ts`
3. Document the component in the feature's `UI-COMPONENTS.md` file
4. Add a Storybook story for the component

## References

- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [Next.js Documentation](https://nextjs.org/docs)
- [ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
- [Developer Documentation Guidelines](./developer_documentation_guidelines.md)
