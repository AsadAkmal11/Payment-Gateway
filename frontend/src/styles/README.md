# CSS File Structure

This directory contains all the CSS files for the Payment Gateway frontend, organized by component and functionality.

## File Structure

```
styles/
├── main.css              # Main CSS file that imports all other styles
├── global.css            # Global styles, utilities, and common components
├── layout.css            # Layout and container styles
├── progress.css          # Progress bar and step indicator styles
├── payment-methods.css   # Payment method selection styles
├── card-preview.css      # Credit card preview component styles
├── real-payment.css      # Real payment form (Stripe) styles
└── README.md            # This documentation file
```

## File Descriptions

### `main.css`
- **Purpose**: Main entry point that imports all other CSS files
- **Usage**: Import this file in your main components
- **Contains**: `@import` statements for all component styles

### `global.css`
- **Purpose**: Global styles and common utilities
- **Contains**:
  - Body and base element styles
  - Utility classes (margins, padding, text alignment)
  - Form styles (inputs, labels, focus states)
  - Button styles (primary, secondary, pay buttons)
  - Alert styles (success, error)
  - Loading spinner animation
  - Input group styles
  - Responsive utilities

### `layout.css`
- **Purpose**: Layout and container styles
- **Contains**:
  - Payment container layout
  - Payment card container
  - Header styles
  - Payment step animations
  - Responsive layout adjustments

### `progress.css`
- **Purpose**: Progress bar and step indicator styles
- **Contains**:
  - Progress bar container
  - Step indicators
  - Active/inactive step states
  - Progress bar line styling
  - Responsive progress bar

### `payment-methods.css`
- **Purpose**: Payment method selection styles
- **Contains**:
  - Payment method grid layout
  - Radio button styling
  - Payment method labels
  - Hover and selected states
  - Card icons
  - Responsive payment methods

### `card-preview.css`
- **Purpose**: Credit card preview component styles
- **Contains**:
  - Card preview container
  - Card front styling (gradient background)
  - Card type, number, and details styling
  - Cardholder name and expiry date
  - Responsive card preview

### `real-payment.css`
- **Purpose**: Real payment form (Stripe integration) styles
- **Contains**:
  - Real payment form container
  - Stripe card element styling
  - Card element focus states
  - Payment button styles
  - Test card information styling
  - Responsive real payment form

## Usage

### In Components
```javascript
// Import the main CSS file in your main component
import './styles/main.css';

// Or import specific styles in component-specific files
import './styles/real-payment.css';
```

### In index.jsx
```javascript
import React from 'react';
import ReactDOM from 'react-dom/client';
import 'bootstrap/dist/css/bootstrap.min.css';
import 'bootstrap/dist/js/bootstrap.bundle.min.js';
import './styles/main.css';  // Import all styles
import App from './App';
```

## Benefits of This Structure

1. **Modularity**: Each CSS file focuses on a specific component or functionality
2. **Maintainability**: Easy to find and modify styles for specific components
3. **Reusability**: Component-specific styles can be imported independently
4. **Organization**: Clear separation of concerns
5. **Scalability**: Easy to add new component styles

## Adding New Styles

1. Create a new CSS file in the `styles/` directory
2. Add the import to `main.css`
3. Import the specific file in your component if needed

### Example
```css
/* styles/new-component.css */
.new-component {
  /* Your styles here */
}
```

```css
/* styles/main.css */
@import './new-component.css';
```

```javascript
// In your component
import './styles/new-component.css';
```

## Best Practices

1. **Use BEM methodology** for class naming when possible
2. **Keep styles scoped** to specific components
3. **Use CSS custom properties** for consistent theming
4. **Include responsive styles** in each component file
5. **Comment your CSS** for complex selectors or animations
6. **Test on multiple screen sizes** after making changes 