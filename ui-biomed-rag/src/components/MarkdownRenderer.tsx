"use client";

import { ReactNode } from "react";

/**
 * Simple markdown renderer without external dependencies.
 * Supports: **bold**, `inline code`, ```code blocks```, [links](url), bare URLs.
 * Handles edge case: strips parentheses wrapping bare URLs to prevent broken links.
 */
export default function MarkdownRenderer({ content }: { content: string }) {

  const renderContent = (text: string) => {
    const parts: ReactNode[] = [];
    let currentIndex = 0;
    let key = 0;

    // Match code blocks ```language\ncode\n```
    const codeBlockRegex = /```(\w+)?\n([\s\S]+?)\n```/g;

    let match;
    const codeBlocks: Array<{
      start: number;
      end: number;
      content: string;
      language?: string;
    }> = [];
    while ((match = codeBlockRegex.exec(text)) !== null) {
      codeBlocks.push({
        start: match.index,
        end: match.index + match[0].length,
        language: match[1],
        content: match[2],
      });
    }

    // Process text with inline formatting (bold, code, links)
    const processInline = (str: string, startKey: number) => {
      const elements: ReactNode[] = [];
      let lastIndex = 0;
      let localKey = startKey;

      // Combined regex: markdown links, bold, inline code, bare URLs
      // For markdown links: capture URL until ) that closes the link (not ) inside URL)
      // Use non-greedy match and look for ) followed by end of string, space, or punctuation
      const combinedRegex =
        /(\[([^\]]+)\]\((https?:\/\/[^\s)]+)\))|(\*\*(.+?)\*\*)|(`([^`]+)`)|(https?:\/\/[^\s<)]+)/g;
      let inlineMatch;

      while ((inlineMatch = combinedRegex.exec(str)) !== null) {
        // Add text before match
        if (inlineMatch.index > lastIndex) {
          elements.push(str.substring(lastIndex, inlineMatch.index));
        }

        if (inlineMatch[2] && inlineMatch[3]) {
          // Markdown link [text](url)
          elements.push(
            <a
              key={`link-${localKey++}`}
              href={inlineMatch[3]}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 underline"
            >
              {inlineMatch[2]}
            </a>
          );
        } else if (inlineMatch[5]) {
          // Bold text
          elements.push(
            <strong
              key={`bold-${localKey++}`}
              className="font-semibold"
            >
              {inlineMatch[5]}
            </strong>
          );
        } else if (inlineMatch[7]) {
          // Inline code
          elements.push(
            <code
              key={`code-${localKey++}`}
              className="rounded bg-gray-200 dark:bg-gray-800 px-1 py-0.5 text-xs"
            >
              {inlineMatch[7]}
            </code>
          );
        } else if (inlineMatch[8]) {
          // Bare URL (not inside a markdown link)
          elements.push(
            <a
              key={`url-${localKey++}`}
              href={inlineMatch[8]}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 underline"
            >
              {inlineMatch[8]}
            </a>
          );
        }

        lastIndex = inlineMatch.index + inlineMatch[0].length;
      }

      // Add remaining text
      if (lastIndex < str.length) {
        elements.push(str.substring(lastIndex));
      }

      return elements.length > 0 ? elements : str;
    };

    // Process text with code blocks
    if (codeBlocks.length > 0) {
      codeBlocks.forEach((block) => {
        if (block.start > currentIndex) {
          const textBefore = text.substring(currentIndex, block.start);
          parts.push(
            <span key={`text-${key++}`}>
              {processInline(textBefore, key)}
            </span>
          );
        }

        parts.push(
          <pre
            key={`block-${key++}`}
            className="mt-2 overflow-x-auto rounded bg-gray-900 p-2 text-xs"
          >
            <code className="text-gray-100">{block.content}</code>
          </pre>
        );

        currentIndex = block.end;
      });

      if (currentIndex < text.length) {
        const textAfter = text.substring(currentIndex);
        parts.push(
          <span key={`text-${key++}`}>
            {processInline(textAfter, key)}
          </span>
        );
      }
    } else {
      return <>{processInline(text, 0)}</>;
    }

    return <>{parts}</>;
  };

  return <div className="whitespace-pre-wrap">{renderContent(content)}</div>;
}
