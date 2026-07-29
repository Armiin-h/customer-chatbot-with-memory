/** Escape HTML entities. */
function escapeHtml(text) {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

/**
 * Lightweight markdown → safe HTML for chat bubbles.
 * Supports: fenced code, inline code, bold, italic, links, lists, paragraphs.
 */
export function markdownToHtml(source) {
  if (!source) {
    return "";
  }

  let text = escapeHtml(source);

  // Fenced code blocks
  text = text.replace(/```([\s\S]*?)```/g, (_match, code) => {
    return `<pre><code>${code.trim()}</code></pre>`;
  });

  // Inline code
  text = text.replace(/`([^`]+)`/g, "<code>$1</code>");

  // Bold then italic
  text = text.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  text = text.replace(/\*([^*]+)\*/g, "<em>$1</em>");

  // Links [label](url) — only allow http(s)
  text = text.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer">$1</a>');

  // Unordered lists
  text = text.replace(/(?:^|\n)(?:- |\* )(.+)(?=\n|$)/g, (_m, item) => `\n<li>${item}</li>`);
  text = text.replace(/(?:<li>.*<\/li>\n?)+/g, (block) => `<ul>${block}</ul>`);

  // Paragraphs / line breaks
  const blocks = text.split(/\n{2,}/).map((block) => {
    const trimmed = block.trim();
    if (!trimmed) {
      return "";
    }
    if (trimmed.startsWith("<pre>") || trimmed.startsWith("<ul>")) {
      return trimmed;
    }
    return `<p>${trimmed.replaceAll("\n", "<br />")}</p>`;
  });

  return blocks.join("");
}
