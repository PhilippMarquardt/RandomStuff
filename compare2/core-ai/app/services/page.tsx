"use client"

import React from 'react';
import { useRouter } from 'next/navigation';
import Header from '../components/Header';

// Service card icons
const PDFCompareIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-8 h-8 text-indigo-600">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
    <line x1="10" y1="12" x2="10" y2="18" />
    <line x1="14" y1="12" x2="14" y2="18" />
  </svg>
);

// Define service types
interface Service {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  route: string;
  available: boolean;
}

const services: Service[] = [
  {
    id: 'pdf-compare',
    title: 'Report Comparison',
    description: 'Compare reports using LLM support',
    icon: <PDFCompareIcon />,
    route: '/services/pdf-compare',
    available: true
  },
  
];

export default function ServicesPage() {
  const router = useRouter();

  const handleServiceClick = (service: Service) => {
    if (service.available) {
      router.push(service.route);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Header 
        title="Services" 
        subtitle=""
      />
      
      <div className="py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">

        {/* Services Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {services.map((service) => (
            <div
              key={service.id}
              onClick={() => handleServiceClick(service)}
              className={`bg-white rounded-lg shadow-sm p-6 border-2 border-transparent transition-all duration-200
                         ${service.available 
                           ? 'hover:border-indigo-500 hover:shadow-lg cursor-pointer' 
                           : 'opacity-60 cursor-not-allowed'}`}
            >
              {/* Service Icon */}
              <div className="mb-4">
                {service.icon}
              </div>

              {/* Service Title */}
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                {service.title}
              </h3>

              {/* Service Description */}
              <p className="text-gray-600 text-sm mb-4">
                {service.description}
              </p>

            </div>
          ))}
        </div>
        
        </div>
      </div>
    </div>
  );
} 