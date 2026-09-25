import { render, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { ShowcasePills } from "./ShowcasePills";

describe("ShowcasePills Component", () => {
  it("renders all 4 showcase corridors", () => {
    const handleSelect = vi.fn();
    const { getByText } = render(
      <ShowcasePills onSelectRoute={handleSelect} />
    );

    expect(getByText(/New York → Dominica/)).toBeDefined();
    expect(getByText(/Miami → Dominica/)).toBeDefined();
    expect(getByText(/Paris → Dominica/)).toBeDefined();
    expect(getByText(/London → Dominica/)).toBeDefined();
  });

  it("calls onSelectRoute with correct origin and destination when clicked", () => {
    const handleSelect = vi.fn();
    const { getByText } = render(
      <ShowcasePills onSelectRoute={handleSelect} />
    );

    const nycButton = getByText(/New York → Dominica/).closest("button");
    expect(nycButton).not.toBeNull();
    if (nycButton) fireEvent.click(nycButton);

    expect(handleSelect).toHaveBeenCalledWith("NYC", "DOM");

    const parButton = getByText(/Paris → Dominica/).closest("button");
    expect(parButton).not.toBeNull();
    if (parButton) fireEvent.click(parButton);

    expect(handleSelect).toHaveBeenCalledWith("PAR", "DOM");
  });
});
