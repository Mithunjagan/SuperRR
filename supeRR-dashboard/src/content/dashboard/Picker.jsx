import React from "react";
import { Menu, MenuItem } from "../../data-app-public.jsx";

export default function Picker({ label, value, options, onChange, variant }) {
  const selectedLabel = options.find(option => option.value === value)?.label ?? value;
  const trigger = (
    <button type="button" className={`rr-picker rr-picker--${variant}`} aria-label={`${label}: ${selectedLabel}`}>
      <span>{selectedLabel}</span>
      <span className="rr-picker-chevron" aria-hidden="true" />
    </button>
  );

  const items = options.map(option => (
    <MenuItem key={option.value} role="menuitemradio" aria-checked={option.value === value}
      onSelect={() => onChange(option.value)}>
      {option.label}
      {option.value === value && <span className="rr-picker-check" aria-hidden="true">✓</span>}
    </MenuItem>
  ));

  return <Menu label={label} trigger={trigger} align={variant === "theme" ? "end" : "start"}
    contentClassName={`rr-picker-menu rr-picker-menu--${variant}`}>{items}</Menu>;
}
