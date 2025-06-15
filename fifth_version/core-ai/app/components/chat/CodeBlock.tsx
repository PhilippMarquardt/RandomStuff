import React, { useState } from 'react';
import { CheckIcon, CopyIcon } from '../icons';
import type { MarkdownNode } from '../../types';

function extractText(node: MarkdownNode): string {
  if (node.type === 'text') {
    return node.value || '';
  }
  if (node.children && Array.isArray(node.children)) {
    return node.children.map(extractText).join('');
  }
  return '';
}

export const CodeBlock = ({ node, children, ...props }: { node?: MarkdownNode; children?: React.ReactNode }) => {
  const [isCopied, setIsCopied] = useState(false);
  
  const codeNode = node?.children?.[0];
  const codeString = codeNode ? extractText(codeNode) : '';

  const handleCopy = () => {
    if (codeString) {
      navigator.clipboard.writeText(codeString).then(() => {
        setIsCopied(true);
        setTimeout(() => setIsCopied(false), 2000);
      });
    }
  };

  return (
    <div className="relative group">
      <pre {...props}>{children}</pre>
      <button
        onClick={handleCopy}
        className="absolute top-2 right-2 p-1.5 bg-gray-800 text-white rounded-md opacity-0 group-hover:opacity-100 transition-opacity"
      >
        {isCopied ? <CheckIcon /> : <CopyIcon />}
      </button>
    </div>
  );
}; 