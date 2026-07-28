export default function FormField({ label, type = "text", value, onChange, placeholder, required = true }) {
  return (
    <label style={{ display: "block", marginBottom: 18 }}>
      <span style={{ display: "block", fontSize: 13, fontWeight: 500, marginBottom: 6, color: "var(--ink)" }}>
        {label}
      </span>
      <input
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        required={required}
        style={{
          width: "100%",
          padding: "11px 14px",
          borderRadius: "var(--radius-sm)",
          border: "1px solid var(--border)",
          background: "var(--surface-alt)",
          color: "var(--ink)",
          fontSize: 14,
          outline: "none",
        }}
        onFocus={(e) => (e.target.style.borderColor = "var(--secondary)")}
        onBlur={(e) => (e.target.style.borderColor = "var(--border)")}
      />
    </label>
  );
}
