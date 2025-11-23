/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    ADMIN_PASSWORD: process.env.ADMIN_PASSWORD,
  },
}

module.exports = nextConfig
