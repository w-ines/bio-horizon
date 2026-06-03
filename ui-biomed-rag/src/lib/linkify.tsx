/**
 * Utility to convert URLs in text to clickable links.
 * Handles both markdown links [text](url) and bare URLs.
 * 
 * Algorithm: 2-pass approach with placeholders to avoid regex conflicts.
 * Pass 1: Replace markdown links [text](url) with safe placeholders
 * Pass 2: Split by placeholders and bare URLs, render each part
 */

import React from 'react';

const LINK_MARKER = '\x00LINK\x00';

export function linkifyText(text: string): React.ReactNode {
  // Pass 1: Extract markdown links and replace with placeholders
  // [Job Status](http://localhost:3000/jobs) → \x00LINK\x00Job Status\x00LINK\x00http://localhost:3000/jobs\x00LINK\x00
  const links: Array<{ text: string; url: string }> = [];
  
  const withPlaceholders = text.replace(
    /\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g,
    (_match, linkText, url) => {
      const index = links.length;
      links.push({ text: linkText, url: url });
      return `${LINK_MARKER}${index}${LINK_MARKER}`;
    }
  );

  console.log('[linkify] Original:', text);
  console.log('[linkify] After placeholder pass:', withPlaceholders);
  console.log('[linkify] Extracted links:', links);
  
  // Pass 2: Split by placeholders and bare URLs
  const parts = withPlaceholders.split(
    new RegExp(`(${LINK_MARKER}\\d+${LINK_MARKER}|https?:\\/\\/[^\\s<]+)`, 'g')
  );
  
  return (
    <>
      {parts.map((part, i) => {
        // Check for markdown link placeholder
        const placeholderMatch = part.match(new RegExp(`^${LINK_MARKER}(\\d+)${LINK_MARKER}$`));
        if (placeholderMatch) {
          const link = links[parseInt(placeholderMatch[1])];
          console.log('[linkify] Rendering markdown link:', link.text, '→', link.url);
          return (
            <a
              key={`mdlink-${i}`}
              href={link.url}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: '#0ea5e9', textDecoration: 'underline', fontWeight: '500' }}
            >
              {link.text}
            </a>
          );
        }
        
        // Check for bare URL
        if (part.match(/^https?:\/\//)) {
          const cleanUrl = part.replace(/[.,;:!?)]+$/, '');
          const trailing = part.slice(cleanUrl.length);
          return (
            <React.Fragment key={`url-${i}`}>
              <a
                href={cleanUrl}
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: '#0ea5e9', textDecoration: 'underline', fontWeight: '500' }}
              >
                {cleanUrl}
              </a>
              {trailing}
            </React.Fragment>
          );
        }
        
        // Plain text
        return part || null;
      })}
    </>
  );
}
