import {defineConfig} from 'vitepress'

// https://vitepress.dev/reference/site-config
export default defineConfig({
    base: '/CrawlerTutorial/',
    title: "程序员阿江-Relakkes的爬虫教程",
    description: "程序员阿江-Relakkes的爬虫教程",
    lastUpdated: true,
    head: [
        [
            'script',
            {async: '', src: 'https://www.googletagmanager.com/gtag/js?id=G-B5H6D2HDGK'}
        ],
        [
            'script',
            {},
            `window.dataLayer = window.dataLayer || [];
      function gtag(){dataLayer.push(arguments);}
      gtag('js', new Date());
      gtag('config', 'G-B5H6D2HDGK');`
        ]
    ],
    themeConfig: {
        editLink: {
            pattern: 'https://github.com/NanmiCoder/CrawlerTutorial/tree/main/docs/:path'
        },
        search: {
            provider: 'local'
        },
        // https://vitepress.dev/reference/default-theme-config
        nav: [
            {text: '首页', link: '/'},
            {text: 'B站主页', link: 'https://space.bilibili.com/434377496'},
            {text: '联系作者', link: 'https://github.com/NanmiCoder'},
        ],

        sidebar: [
            {
                text: 'Python爬虫入门',
                collapsed: false,
                items: [
                    {text: '01_为什么要写这个爬虫教程', link: '/爬虫入门/01_为什么要写这个爬虫教程'},
                    {text: '02_个人学会爬虫能赚钱吗', link: '/爬虫入门/02_个人学会爬虫能赚钱吗'},
                    {text: '03_网络爬虫到底是什么', link: '/爬虫入门/03_网络爬虫到底是什么'},
                    {text: '04_爬虫的基本工作原理', link: '/爬虫入门/04_爬虫的基本工作原理'},
                    {text: '05_常用的抓包工具有那些', link: '/爬虫入门/05_常用的抓包工具有那些'},
                    {
                        text: '06_Python写爬虫的优势',
                        link: '/爬虫入门/06_为什么说用Python写爬虫有天生优势'
                    },
                    {text: '07_Python常见的网络请求库', link: '/爬虫入门/07_Python常见的网络请求库'},
                    {text: '08_入门实战1_静态网页数据提取', link: '/爬虫入门/08_爬虫入门实战1_静态网页数据提取'},
                    {text: '09_入门实战2_动态数据提取', link: '/爬虫入门/09_爬虫入门实战2_动态数据提取'},
                    {text: '10_入门实战3_数据存储实现', link: '/爬虫入门/10_爬虫入门实战3_数据存储实现'},
                    {text: '11_入门实战4_高效率的爬虫实现', link: '/爬虫入门/11_爬虫入门实战4_高效率的爬虫实现'},
                    {
                        text: '12_入门实战5_编写易于维护的代码',
                        link: '/爬虫入门/12_爬虫入门实战5_编写易于维护的爬虫代码'
                    }
                ]
            }
        ],

        socialLinks: [
            {icon: 'github', link: 'https://github.com/NanmiCoder/CrawlerTutorial'}
        ]
    },

})
