import { themes as prismThemes } from 'prism-react-renderer';
import type { Config } from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'علوم داده، پیشنهادی فردوسی مشهد',
  favicon: 'img/dslab-logo.ico',

  // Set the production url of your site here
  // url: 'https://fum-ds.github.io',
  // // Set the /<baseUrl>/ pathname under which your site is served
  // // For GitHub pages deployment, it is often '/<projectName>/'
  // baseUrl: '',

  url: 'https://mamintoosi.ir',
  baseUrl: '/fum-ds/', // ← حتماً / در ابتدا و انتها

  // GitHub pages deployment config.
  // If you aren't using GitHub pages, you don't need these.
  organizationName: 'Ferdowsi University of Mashhad, CS Dept.', // Usually your GitHub org/user name.
  projectName: 'fumds-docs', // Usually your repo name.

  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',

  // Even if you don't use internationalization, you can use this field to set
  // useful metadata like html lang. For example, if your site is Chinese, you
  // may want to replace "en" with "zh-Hans".
  i18n: {
    defaultLocale: 'fa',
    locales: ['fa'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
        },
        blog: {
          showReadingTime: true,
        },
        theme: {
          customCss: ['./src/css/custom.css', './src/css/font.css'],
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    // Replace with your project's social card
    image: 'img/docusaurus-social-card.jpg',
    navbar: {
      title: 'علوم داده',
      logo: {
        alt: 'FUMDS Logo',
        src: 'img/dslab-logo.png',
      },
      items: [
        {
          href: '/docs',
          label: 'مستندات',
          position: 'left',
        },
        {
          href: 'https://www.um.ac.ir',
          label: 'FUM',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'مستندات',
          items: [
            {
              label: 'برنامه درسی',
              to: '/docs/category/curriculum',
            },
          ],
        },
        {
          title: 'لینک‌ها',
          items: [
            {
              label: 'Dr. M. Arashi',
              to: 'https://prof.um.ac.ir/arashi',
            },
            // {
            //   label: 'GitHub',
            //   href: 'https://github.com/fum-ds/fum-ds.github.io',
            // },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} FUMCS, Inc`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
    },
    algolia: {
      // The application ID provided by Algolia
      appId: 'IW0UML0UCO',

      apiKey: '0f98e980c17dabdb99e47db17c02e055',

      indexName: 'fumds_curriculum',
    },
  } satisfies Preset.ThemeConfig,
  themes: [
    [
      require.resolve('@easyops-cn/docusaurus-search-local'),
      /** @type {import("@easyops-cn/docusaurus-search-local").PluginOptions} */
      {
        // `hashed` is recommended as long-term-cache of index file is possible.
        hashed: true,
        language: ['en', 'fa'],
      },
    ],
  ],
};

export default config;
