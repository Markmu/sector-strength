"use client";

import React, { useState, useEffect, useRef } from 'react';
import { Search, X, ChevronDown, Loader2 } from 'lucide-react';
import { sectorsApi } from '@/lib/api';

interface SectorOption {
  id: number;
  code: string;
  name: string;
  type: string;
  label: string;
  value: number;
}

interface SectorSearchSelectProps {
  value: number | null;
  onChange: (value: number | null) => void;
  disabled?: boolean;
  placeholder?: string;
  sectorType?: 'industry' | 'concept';
}

/**
 * 板块搜索选择器
 *
 * 支持搜索板块名称或代码的下拉选择框
 */
export default function SectorSearchSelect({
  value,
  onChange,
  disabled = false,
  placeholder = '搜索板块...',
  sectorType
}: SectorSearchSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [options, setOptions] = useState<SectorOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedSector, setSelectedSector] = useState<SectorOption | null>(null);

  const dropdownRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // 点击外部关闭下拉框
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // 加载初始选中的板块信息
  useEffect(() => {
    if (value && !selectedSector) {
      // 如果有值但没有选中板块信息，尝试搜索
      handleSearch(value.toString());
    }
  }, [value]);

  // 搜索板块
  const handleSearch = async (keyword: string) => {
    if (!keyword || keyword.length < 1) {
      setOptions([]);
      return;
    }

    setLoading(true);
    try {
      console.log('[SectorSearchSelect] 搜索板块:', keyword);
      const response = await sectorsApi.searchSectors(keyword, {
        sector_type: sectorType,
        limit: 20
      });

      console.log('[SectorSearchSelect] API响应:', response);

      // response.data 是 { success: true, data: [...] }
      // 需要提取真正的数据数组
      if (response.data && response.data.data) {
        const sectors = response.data.data;
        console.log('[SectorSearchSelect] 搜索结果:', sectors);
        setOptions(sectors);
      } else {
        console.log('[SectorSearchSelect] 无搜索结果');
        setOptions([]);
      }
    } catch (error) {
      console.error('[SectorSearchSelect] 搜索板块失败:', error);
      setOptions([]);
    } finally {
      setLoading(false);
    }
  };

  // 防抖搜索
  const handleInputChange = (text: string) => {
    setSearchText(text);

    // 当用户输入时，确保下拉框是打开的
    if (!isOpen && text.length > 0) {
      setIsOpen(true);
    }

    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    searchTimeoutRef.current = setTimeout(() => {
      handleSearch(text);
    }, 300);
  };

  // 选择板块
  const handleSelectSector = (sector: SectorOption) => {
    setSelectedSector(sector);
    onChange(sector.value);
    setSearchText(sector.label);
    setIsOpen(false);
  };

  // 清除选择
  const handleClear = () => {
    setSelectedSector(null);
    onChange(null);
    setSearchText('');
    setOptions([]);
    inputRef.current?.focus();
  };

  // 获取显示文本
  const getDisplayText = () => {
    if (selectedSector) {
      return selectedSector.label;
    }
    return searchText;
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* 输入框 */}
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          value={getDisplayText()}
          onChange={(e) => handleInputChange(e.target.value)}
          onFocus={() => setIsOpen(true)}
          placeholder={placeholder}
          disabled={disabled}
          className={`
            w-full px-4 py-2 pr-20 border rounded-lg
            focus:ring-2 focus:ring-blue-500 focus:border-transparent
            disabled:opacity-50 disabled:cursor-not-allowed
            ${isOpen ? 'ring-2 ring-blue-500 border-blue-500' : 'border-gray-300'}
          `}
        />

        {/* 右侧图标 */}
        <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
          {loading && (
            <Loader2 className="w-4 h-4 text-gray-400 animate-spin" />
          )}
          {selectedSector && !disabled && (
            <button
              onClick={handleClear}
              className="p-1 hover:bg-gray-100 rounded-full transition-colors"
              type="button"
            >
              <X className="w-4 h-4 text-gray-400" />
            </button>
          )}
          <button
            onClick={() => {
              if (!disabled) {
                setIsOpen(!isOpen);
                inputRef.current?.focus();
              }
            }}
            className="p-1 hover:bg-gray-100 rounded-full transition-colors"
            type="button"
          >
            <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
          </button>
        </div>
      </div>

      {/* 下拉列表 */}
      {isOpen && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-auto">
          {loading && options.length === 0 ? (
            <div className="px-4 py-8 text-center text-gray-500">
              <Loader2 className="w-6 h-6 mx-auto mb-2 animate-spin" />
              <p className="text-sm">搜索中...</p>
            </div>
          ) : options.length > 0 ? (
            <ul className="py-1">
              {options.map((sector) => (
                <li
                  key={sector.id}
                  onClick={() => handleSelectSector(sector)}
                  className={`
                    px-4 py-2 cursor-pointer transition-colors
                    hover:bg-blue-50
                    ${selectedSector?.id === sector.id ? 'bg-blue-50 text-blue-700' : 'text-gray-700'}
                  `}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{sector.name}</span>
                    <span className="text-sm text-gray-500 ml-2">({sector.code})</span>
                  </div>
                  <div className="text-xs text-gray-400 mt-0.5">
                    {sector.type === 'industry' ? '行业板块' : '概念板块'}
                  </div>
                </li>
              ))}
            </ul>
          ) : searchText.length >= 1 ? (
            <div className="px-4 py-8 text-center text-gray-500">
              <Search className="w-6 h-6 mx-auto mb-2 text-gray-300" />
              <p className="text-sm">未找到匹配的板块</p>
              <p className="text-xs text-gray-400 mt-1">请尝试其他关键词</p>
            </div>
          ) : (
            <div className="px-4 py-8 text-center text-gray-500">
              <Search className="w-6 h-6 mx-auto mb-2 text-gray-300" />
              <p className="text-sm">输入板块名称或代码搜索</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
