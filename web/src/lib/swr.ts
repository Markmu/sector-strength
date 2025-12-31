import useSWR, { SWRConfiguration } from 'swr';

/**
 * 通用 fetcher 函数
 */
const fetcher = async (url: string) => {
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
};

/**
 * 默认 SWR 配置
 */
export const defaultSWRConfig: SWRConfiguration = {
  revalidateOnFocus: false,
  revalidateOnReconnect: true,
  shouldRetryOnError: true,
  dedupingInterval: 1000,
};

/**
 * 仪表板数据获取 Hook
 */
export function useDashboardData<T = any>(key: string | string[], config?: SWRConfiguration) {
  return useSWR<T>(
    key,
    fetcher,
    { ...defaultSWRConfig, ...config }
  );
}

/**
 * 健康检查 Hook
 */
export function useHealthCheck() {
  return useSWR<{ status: string; timestamp: string }>(
    '/api/health',
    fetcher,
    {
      ...defaultSWRConfig,
      refreshInterval: 30000, // 每30秒检查一次
    }
  );
}

export default fetcher;
