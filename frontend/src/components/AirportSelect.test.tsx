import { render, screen, fireEvent } from '@testing-library/react';
import { describe, test, expect, vi } from 'vitest';
import { AirportSelect } from './AirportSelect';

describe('AirportSelect Component', () => {
  test('renders label and placeholder correctly', () => {
    const mockOnChange = vi.fn();
    render(
      <AirportSelect 
        label="Departure" 
        value="" 
        onChange={mockOnChange} 
        placeholder="Enter airport" 
      />
    );
    expect(screen.getByText('Departure')).toBeDefined();
    expect(screen.getByPlaceholderText('Enter airport')).toBeDefined();
  });

  test('calls onChange with uppercase value when typing', () => {
    const mockOnChange = vi.fn();
    render(
      <AirportSelect 
        label="Departure" 
        value="" 
        onChange={mockOnChange} 
      />
    );
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'jfk' } });
    expect(mockOnChange).toHaveBeenCalledWith('JFK');
  });
});
