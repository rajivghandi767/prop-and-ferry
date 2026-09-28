import { render } from '@testing-library/react';
import { describe, test, expect } from 'vitest';
import App from './App';

describe('App Component', () => {
  test('renders without crashing', () => {
    const { container } = render(<App />);
    expect(container).toBeDefined();
  });

  test('renders condensed proof of concept notice', () => {
    const { getByText } = render(<App />);
    expect(getByText(/Portfolio demo/)).toBeDefined();
    expect(getByText(/Gateways: NYC · MIA · CLT · LON · PAR/)).toBeDefined();
  });
});

