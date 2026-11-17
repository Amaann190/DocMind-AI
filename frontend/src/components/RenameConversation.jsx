import React, { useState } from "react";
import { Modal } from "./ui.jsx";

export function RenameConversation({ conversation, close, save, disabled }) {
  const [title, setTitle] = useState(conversation.title);
  return (
    <Modal title="Rename conversation" close={close}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          save(title.trim());
        }}
      >
        <label className="rename-label">
          Conversation name
          <input
            autoFocus
            value={title}
            maxLength={100}
            required
            onChange={(e) => setTitle(e.target.value)}
          />
        </label>
        <div className="modal-footer">
          <button className="primary" disabled={disabled || !title.trim()}>
            Save name
          </button>
        </div>
      </form>
    </Modal>
  );
}
