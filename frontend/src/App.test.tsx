import { render } from '@testing-library/react';
import { describe, test, expect } from 'vitest';
import App from './App';

describe('App Component', () => {
  test('renders without crashing', () => {
    const { container } = render(<App />);
    expect(container).toBeDefined();
  });

  test('renders updated proof of concept notice with full gateway network', () => {
    const { getByText } = render(<App />);
    expect(getByText(/⚠️ Proof of Concept Notice:/)).toBeDefined();
    expect(getByText(/Miami \(MIA\)/)).toBeDefined();
    expect(getByText(/Charlotte \(CLT\)/)).toBeDefined();
  });
});

