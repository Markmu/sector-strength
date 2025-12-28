/**
 * Dashboard Dependencies Test
 * Tests that required dependencies are installed and available
 */

describe('Dashboard Dependencies', () => {
  describe('shadcn/ui dependencies', () => {
    it('should have clsx installed', () => {
      expect(require('clsx')).toBeDefined();
    });

    it('should have tailwind-merge installed', () => {
      expect(require('tailwind-merge')).toBeDefined();
    });

    it('should have class-variance-authority installed', () => {
      expect(require('class-variance-authority')).toBeDefined();
    });

    it('should have tailwindcss-animate installed', () => {
      expect(require('tailwindcss-animate')).toBeDefined();
    });
  });

  describe('lucide-react icons', () => {
    it('should have lucide-react installed', () => {
      expect(require('lucide-react')).toBeDefined();
    });
  });

  describe('SWR data fetching', () => {
    it('should have swr installed', () => {
      expect(require('swr')).toBeDefined();
    });
  });
});
