import Editor, { type OnMount } from "@monaco-editor/react";
import { monacoLanguageForPath } from "@/lib/codeFileTree";

type Props = {
  path: string;
  value: string;
  onChange: (value: string) => void;
  readOnly?: boolean;
};

export function CodeMonacoEditor({ path, value, onChange, readOnly }: Props) {
  const language = monacoLanguageForPath(path);

  const onMount: OnMount = (editor) => {
    editor.focus();
  };

  return (
    <Editor
      height="100%"
      language={language}
      value={value}
      theme="vs"
      onMount={onMount}
      onChange={(v) => onChange(v ?? "")}
      options={{
        readOnly,
        minimap: { enabled: false },
        fontSize: 13,
        lineHeight: 20,
        fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
        scrollBeyondLastLine: false,
        wordWrap: "on",
        automaticLayout: true,
        tabSize: 2,
        padding: { top: 12 },
      }}
    />
  );
}
