import React from "react";

export function PassagePreview({ source, sources }) {
  const document = sources.find((s) => s.id === source.source_id);
  const text = document?.preview || "";
  const position = source.text ? text.indexOf(source.text) : -1;
  return (
    <>
      {source.number && (
        <p className="citation-explanation">
          Highlighted text was retrieved for this answer.
          {source.page != null
            ? ` Page ${source.page}.`
            : " Page information is not available for this passage."}
        </p>
      )}
      <div className="source-preview">
        {source.number ? (
          position >= 0 ? (
            <>
              {text.slice(Math.max(0, position - 350), position)}
              <mark>{source.text}</mark>
              {text.slice(
                position + source.text.length,
                position + source.text.length + 350,
              )}
            </>
          ) : (
            <mark>{source.text}</mark>
          )
        ) : (
          source.preview || source.error || "No text preview available."
        )}
      </div>
    </>
  );
}
