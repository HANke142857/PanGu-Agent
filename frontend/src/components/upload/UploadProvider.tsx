import { createContext, useContext, useState, type ReactNode } from "react";
import { UploadDrawer } from "./UploadDrawer";

const UploadContext = createContext<{ open: () => void }>({ open: () => {} });

// eslint-disable-next-line react-refresh/only-export-components
export function useUpload() {
  return useContext(UploadContext);
}

export function UploadProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <UploadContext.Provider value={{ open: () => setOpen(true) }}>
      {children}
      <UploadDrawer open={open} onClose={() => setOpen(false)} />
    </UploadContext.Provider>
  );
}
