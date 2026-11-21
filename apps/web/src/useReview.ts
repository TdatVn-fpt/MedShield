// apps/web/src/useReview.ts — Manage review versions, asynchronous previews and approval.
import { useRef, useState } from 'react';
import { downloadResult, requestJson } from './api';
import type { Analysis, Engine, Entity, Redaction } from './types';

/** useReview keeps text in memory and rejects responses from any obsolete document revision. */
export function useReview() {
  const revision = useRef(0);
  const [text, setText] = useState('');
  const [entities, setEntities] = useState<Entity[]>([]);
  const [preview, setPreview] = useState<Redaction | null>(null);
  const [engine, setEngine] = useState<Engine | null>(null);
  const [approved, setApproved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [analyzed, setAnalyzed] = useState(false);
  const [error, setError] = useState('');
  const [language, setLanguage] = useState<'vi' | 'en'>('vi');
  const [mode, setMode] = useState<'rules' | 'ner' | 'hybrid'>('rules');

  /** changeText invalidates all machine results and approval before accepting new input. */
  function changeText(value: string): void {
    revision.current += 1;
    setText(value);
    setEntities([]);
    setPreview(null);
    setEngine(null);
    setApproved(false);
    setAnalyzed(false);
    setBusy(false);
    setError('');
  }

  /** reportError clears export authorization and displays a safe Vietnamese error. */
  function reportError(message: string): void {
    revision.current += 1;
    setError(message);
    setPreview(null);
    setApproved(false);
    setBusy(false);
  }

  /** analyze calls the selected real engine and obtains a version-matched redaction preview. */
  async function analyze(): Promise<boolean> {
    if (!text.trim() || Array.from(text).length > 50000) return false;
    const current = ++revision.current;
    setApproved(false);
    setPreview(null);
    setError('');
    setBusy(true);
    try {
      const result = await requestJson<Analysis>('/api/analyze', { text, language, mode });
      if (revision.current !== current) return false;
      const redacted = await requestJson<Redaction>('/api/redact', {
        text,
        entities: result.entities,
      });
      if (revision.current !== current) return false;
      setEntities(result.entities);
      setEngine(result.engine);
      setPreview(redacted);
      setAnalyzed(true);
      return true;
    } catch (cause) {
      if (revision.current === current) {
        setError(cause instanceof Error ? cause.message : 'Không kết nối được API.');
      }
      return false;
    } finally {
      if (revision.current === current) setBusy(false);
    }
  }

  /** changeEntities previews the exact reviewed list and blocks late responses after later edits. */
  async function changeEntities(next: Entity[]): Promise<void> {
    const current = ++revision.current;
    setEntities(next);
    setApproved(false);
    setPreview(null);
    setError('');
    setBusy(true);
    try {
      const result = await requestJson<Redaction>('/api/redact', { text, entities: next });
      if (revision.current === current) setPreview(result);
    } catch (cause) {
      if (revision.current === current) {
        setError(cause instanceof Error ? cause.message : 'Không kết nối được API.');
      }
    } finally {
      if (revision.current === current) setBusy(false);
    }
  }

  /** exportFile downloads only the latest preview after explicit approval. */
  function exportFile(format: 'txt' | 'json'): void {
    if (!preview || !approved || busy) return;
    downloadResult(
      format === 'txt' ? preview.redacted_text : JSON.stringify(preview, null, 2),
      format,
    );
  }

  /** changeConfiguration clears previous results when language or detection mode changes. */
  function changeConfiguration(nextLanguage: 'vi' | 'en', nextMode: typeof mode): void {
    changeText(text);
    setLanguage(nextLanguage);
    setMode(nextMode);
  }

  return {
    text,
    entities,
    preview,
    engine,
    approved,
    busy,
    analyzed,
    error,
    language,
    mode,
    changeText,
    reportError,
    analyze,
    changeEntities,
    exportFile,
    changeConfiguration,
    setApproved,
  };
}
