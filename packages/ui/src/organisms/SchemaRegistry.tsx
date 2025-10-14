import * as React from 'react';
import { tokens } from '../tokens';
import { Input } from '../atoms/Input';
export const SchemaRegistry: React.FC = () => (
  <section role="region" aria-label="Schema Registry" style={{ padding: tokens.spacing.md }}>
    <h1 style={{ fontSize: tokens.typography.fontSize.xl, marginTop: 0 }}>Schema Registry</h1>
    <form aria-labelledby="schema-form">
      <div style={{ marginBottom: tokens.spacing.sm }}>
        <label htmlFor="schemaName">Schema name</label><br />
        <Input id="schemaName" name="schemaName" aria-describedby="schemaNameHelp" />
        <div id="schemaNameHelp">Provide a unique, descriptive name.</div>
      </div>
      <div role="alert" aria-live="assertive" style={{ display: 'none' }}>Validation error will appear here</div>
      <button type="submit" style={{ marginTop: tokens.spacing.sm }}>Save</button>
    </form>
  </section>
);
