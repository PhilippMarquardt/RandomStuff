"use client";

import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';

interface PDFAnnotationSettings {
  defaultChatModel: string;
  defaultVisionModel: string;
  availableModels: string[];
}

interface PDFAnnotationContextType {
  settings: PDFAnnotationSettings;
  updateDefaultChatModel: (model: string) => void;
  updateDefaultVisionModel: (model: string) => void;
  setAvailableModels: (models: string[]) => void;
}

const PDFAnnotationContext = createContext<PDFAnnotationContextType | undefined>(undefined);

export const PDFAnnotationProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [settings, setSettings] = useState<PDFAnnotationSettings>({
    defaultChatModel: '',
    defaultVisionModel: '',
    availableModels: [],
  });

  const updateDefaultChatModel = useCallback((model: string) => {
    setSettings(prev => ({ ...prev, defaultChatModel: model }));
  }, []);

  const updateDefaultVisionModel = useCallback((model: string) => {
    setSettings(prev => ({ ...prev, defaultVisionModel: model }));
  }, []);

  const setAvailableModels = useCallback((models: string[]) => {
    setSettings(prev => ({
      ...prev,
      availableModels: models,
      // Set defaults to first available model if not already set
      defaultChatModel: prev.defaultChatModel || models[0] || '',
      defaultVisionModel: prev.defaultVisionModel || models[0] || '',
    }));
  }, []);

  return (
    <PDFAnnotationContext.Provider 
      value={{ 
        settings, 
        updateDefaultChatModel, 
        updateDefaultVisionModel,
        setAvailableModels 
      }}
    >
      {children}
    </PDFAnnotationContext.Provider>
  );
};

export const usePDFAnnotationSettings = () => {
  const context = useContext(PDFAnnotationContext);
  if (!context) {
    throw new Error('usePDFAnnotationSettings must be used within a PDFAnnotationProvider');
  }
  return context;
}; 