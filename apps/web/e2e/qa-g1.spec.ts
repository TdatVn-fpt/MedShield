// apps/web/e2e/qa-g1.spec.ts — Verify real request ordering, Unicode selection and downloaded bytes.
import { readFile } from 'node:fs/promises';
import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';

const name = 'La\u0302m Thu';
const note = `🧪 Người bệnh ${name}; gọi lại cho ${name}.\r\nMã HS-7284. Tái khám 07/11.`;
const original = 'Văn bản gốc có đánh dấu';
const approval = 'Tôi đã rà soát toàn bộ nội dung';

/** deferred returns a promise the test can resolve to order genuine HTTP responses. */
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

/** waitForUi gives the browser two frames to apply a response it has finished reading. */
async function waitForUi(page: Page): Promise<void> {
  await page.evaluate(
    () =>
      new Promise<void>((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
      ),
  );
}

test('BOM upload, Unicode edits and late redact preserve the approved TXT and JSON bytes', async ({
  page,
  browser,
}) => {
  await page.goto('/');
  const file = page.getByLabel('Tải tệp TXT UTF-8', { exact: true });
  const analyze = page.getByRole('button', { name: 'Phân tích', exact: true });
  await expect(analyze).toBeDisabled();
  await file.setInputFiles({
    name: 'qa-private-fixture.txt',
    mimeType: 'text/plain',
    buffer: Buffer.from('\uFEFF' + note, 'utf8'),
  });
  await expect(page.getByRole('textbox', { name: 'Văn bản gốc', exact: true })).toHaveValue(
    note.replace('\r\n', '\n'),
  );
  const analyzed = page.waitForResponse((response) => response.url().endsWith('/api/analyze'));
  await analyze.click();
  const analysis = await analyzed;
  expect(analysis.status()).toBe(200);
  expect(analysis.request().postDataJSON()).toEqual({ text: note, language: 'vi', mode: 'rules' });
  const { engine, entities } = await analysis.json();
  const [initialName, repeatedName, recordId] = entities;
  expect(engine.name).toBe('medshield-rules');

  const source = page.getByLabel(original, { exact: true });
  const preview = page.getByLabel('Bản đã che', { exact: true }).locator('p.redacted-text');
  const approve = page.getByRole('checkbox', { name: approval });
  const txt = page.getByRole('button', { name: 'Tải TXT', exact: true });
  const json = page.getByRole('button', { name: 'Tải JSON', exact: true });
  await expect(source).toBeVisible();
  expect(await source.textContent()).toBe(note);
  await expect(txt).toBeDisabled();
  await expect(json).toBeDisabled();
  const locate = page.getByRole('button', { name: 'Định vị phát hiện 1', exact: true });
  await locate.press('Enter');
  await expect(source.locator('mark').first()).toBeFocused();
  await expect(source.locator('mark').first()).toHaveText(name);

  const start = Array.from(note.slice(0, note.lastIndexOf(name))).length;
  expect(repeatedName).toMatchObject({
    start,
    end: start + Array.from(name).length,
    label: 'NAME',
    source: 'medshield-rules+exact-name-repeat',
  });
  await expect(
    page.getByRole('button', { name: 'Định vị phát hiện 2', exact: true }),
  ).toContainText('medshield-rules+exact-name-repeat');
  const removed = page.waitForResponse((response) => response.url().endsWith('/api/redact'));
  await page.getByRole('button', { name: 'Bỏ phát hiện 2', exact: true }).click();
  const removeResponse = await removed;
  expect(removeResponse.status()).toBe(200);
  expect(removeResponse.request().postDataJSON().entities).toEqual([initialName, recordId]);
  await expect
    .poll(() => preview.textContent())
    .toBe(`🧪 Người bệnh [NAME_1]; gọi lại cho ${name}.\r\nMã [ID_1]. Tái khám 07/11.`);

  await source.evaluate((element, value) => {
    const node = [...element.childNodes].find(
      (child) => child.nodeType === Node.TEXT_NODE && child.textContent?.includes(value),
    );
    if (!node?.textContent) throw new Error('Manual QA selection target was not found');
    const start = node.textContent.indexOf(value);
    const range = document.createRange();
    range.setStart(node, start);
    range.setEnd(node, start + value.length);
    const selection = window.getSelection()!;
    selection.removeAllRanges();
    selection.addRange(range);
    element.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
  }, name);
  const added = page.waitForResponse((response) => response.url().endsWith('/api/redact'));
  await page.getByRole('button', { name: 'Thêm vùng che', exact: true }).click();
  const addResponse = await added;
  expect(addResponse.status()).toBe(200);
  expect(addResponse.request().postDataJSON().entities).toContainEqual({
    start,
    end: start + Array.from(name).length,
    label: 'NAME',
    source: 'manual',
    score: 1,
  });
  const expected = '🧪 Người bệnh [NAME_1]; gọi lại cho [NAME_1].\r\nMã [ID_1]. Tái khám 07/11.';
  await expect.poll(() => preview.textContent()).toBe(expected);
  await approve.check();
  await expect(txt).toBeEnabled();

  const hold = deferred<void>();
  const reachedApi = deferred<string>();
  await page.route('**/api/redact', async (route) => {
    const { entities } = route.request().postDataJSON();
    if (!entities.some((entity: { label: string }) => entity.label === 'ADDR')) {
      await route.continue();
      return;
    }
    const old = await route.fetch();
    reachedApi.resolve((await old.json()).redacted_text);
    await hold.promise;
    await route.fulfill({ response: old });
  });
  const changedLabel = page.getByLabel('Nhãn phát hiện 3', { exact: true });
  try {
    await changedLabel.selectOption('ADDR');
    expect(await reachedApi.promise).toBe(expected.replace('[ID_1]', '[ADDR_1]'));
    await expect(preview).toHaveCount(0);
    await expect(approve).not.toBeChecked();
    await expect(txt).toBeDisabled();
    await expect(json).toBeDisabled();
    await changedLabel.selectOption('ID');
    await expect.poll(() => preview.textContent()).toBe(expected);
    await expect(txt).toBeDisabled();
    await approve.check();
    const obsolete = page.waitForResponse(
      (response) =>
        response.url().endsWith('/api/redact') &&
        response.request().postDataJSON().entities[2].label === 'ADDR',
    );
    hold.resolve();
    const old = await obsolete;
    expect(old.status()).toBe(200);
    expect(await old.finished()).toBeNull();
    await waitForUi(page);
    expect(await preview.textContent()).toBe(expected);
    await expect(changedLabel).toHaveValue('ID');
    await expect(approve).toBeChecked();
  } finally {
    hold.resolve();
  }

  const downloads = [];
  for (const button of [txt, json]) {
    const pending = page.waitForEvent('download');
    await button.click();
    const download = await pending;
    const path = await download.path();
    expect(path).toBeTruthy();
    downloads.push(await readFile(path!));
  }
  expect(downloads[0]).toEqual(Buffer.from(expected, 'utf8'));
  const payload = {
    redacted_text: expected,
    metadata: {
      entity_count: 3,
      counts_by_label: { NAME: 2, DOB: 0, PHONE: 0, ID: 1, ADDR: 0 },
      offset_unit: 'unicode_code_point',
    },
  };
  const decoded = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(downloads[1]);
  expect(JSON.parse(decoded)).toEqual(payload);
  console.log(
    `QA Chromium ${browser.version()}; TXT ${downloads[0].length} bytes; JSON ${downloads[1].length} bytes`,
  );
});

test('a late real analyze cannot replace the approved newer analysis', async ({ page }) => {
  const oldText = 'Người bệnh Hà San. Hẹn 12/11.';
  const newText = 'Người bệnh Đinh Mây. Hẹn 13/11.';
  const expected = 'Người bệnh [NAME_1]. Hẹn 13/11.';
  const hold = deferred<void>();
  const reachedApi = deferred<string>();
  const submittedRedactions: string[] = [];
  page.on('request', (request) => {
    if (request.url().endsWith('/api/redact')) {
      submittedRedactions.push(request.postDataJSON().text);
    }
  });
  await page.route('**/api/analyze', async (route) => {
    if (route.request().postDataJSON().text !== oldText) {
      await route.continue();
      return;
    }
    const old = await route.fetch();
    reachedApi.resolve((await old.json()).redacted_text);
    await hold.promise;
    await route.fulfill({ response: old });
  });
  await page.goto('/');
  const input = page.getByRole('textbox', { name: 'Văn bản gốc', exact: true });
  const analyze = page.getByRole('button', { name: 'Phân tích', exact: true });
  const approve = page.getByRole('checkbox', { name: approval });
  const preview = page.getByLabel('Bản đã che', { exact: true }).locator('p.redacted-text');
  try {
    await input.fill(oldText);
    await analyze.click();
    expect(await reachedApi.promise).toContain('12/11');
    await expect(page.getByRole('button', { name: 'Đang xử lý…' })).toBeDisabled();
    await input.fill(newText);
    await analyze.click();
    await expect(preview).toHaveText(expected);
    await approve.check();
    const obsolete = page.waitForResponse(
      (response) =>
        response.url().endsWith('/api/analyze') &&
        response.request().postDataJSON().text === oldText,
    );
    hold.resolve();
    const old = await obsolete;
    expect(old.status()).toBe(200);
    expect(await old.finished()).toBeNull();
    await waitForUi(page);
    expect(await preview.textContent()).toBe(expected);
    expect(submittedRedactions).toEqual([newText]);
    await expect(page.getByLabel(original, { exact: true })).toHaveText(newText);
    await expect(approve).toBeChecked();
  } finally {
    hold.resolve();
  }
});

test('TXT import consumes exactly one BOM and rejects malformed UTF-8', async ({ page }) => {
  const text = '\uFEFFGhi chú BOM giả lập.';
  await page.goto('/');
  const file = page.getByLabel('Tải tệp TXT UTF-8', { exact: true });
  const input = page.getByRole('textbox', { name: 'Văn bản gốc', exact: true });
  await file.setInputFiles({
    name: 'qa-double-bom.txt',
    mimeType: 'text/plain',
    buffer: Buffer.from('\uFEFF' + text, 'utf8'),
  });
  await expect(input).toHaveValue(text);
  const response = page.waitForResponse((result) => result.url().endsWith('/api/analyze'));
  await page.getByRole('button', { name: 'Phân tích', exact: true }).click();
  expect((await response).request().postDataJSON().text).toBe(text);
  await page.getByRole('checkbox', { name: approval }).check();
  await file.setInputFiles({
    name: 'qa-invalid-utf8.txt',
    mimeType: 'text/plain',
    buffer: Buffer.from([0xc3, 0x28]),
  });
  await expect(page.getByRole('alert')).toContainText('Không đọc được TXT UTF-8');
  await expect(page.getByLabel(original, { exact: true })).toHaveText('Ghi chú BOM giả lập.');
  await expect(page.getByRole('checkbox', { name: approval })).not.toBeChecked();
  await expect(page.getByRole('button', { name: 'Tải TXT', exact: true })).toBeDisabled();
});

test('a pending TXT read cannot replace newer typed input', async ({ page }) => {
  await page.goto('/');
  const pendingRead = await page.evaluateHandle(() => {
    const nativeRead = File.prototype.arrayBuffer;
    let release!: () => void;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    let started = false;
    let finished = false;
    File.prototype.arrayBuffer = async function () {
      started = true;
      await gate;
      const bytes = await nativeRead.call(this);
      finished = true;
      return bytes;
    };
    return { started: () => started, finished: () => finished, release };
  });
  await page.getByLabel('Tải tệp TXT UTF-8', { exact: true }).setInputFiles({
    name: 'qa-old-upload.txt',
    mimeType: 'text/plain',
    buffer: Buffer.from('Tệp cũ giả lập.', 'utf8'),
  });
  await expect.poll(() => pendingRead.evaluate((read) => read.started())).toBe(true);
  const text = 'Nội dung nhập sau khi chọn tệp.';
  await page.getByRole('textbox', { name: 'Văn bản gốc', exact: true }).fill(text);
  await pendingRead.evaluate((read) => read.release());
  await expect.poll(() => pendingRead.evaluate((read) => read.finished())).toBe(true);
  await waitForUi(page);
  const analyzed = page.waitForResponse((response) => response.url().endsWith('/api/analyze'));
  await page.getByRole('button', { name: 'Phân tích', exact: true }).click();
  expect((await analyzed).request().postDataJSON().text).toBe(text);
});
