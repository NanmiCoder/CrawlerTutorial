import {defineConfig} from 'vitepress'
import {withMermaid} from 'vitepress-plugin-mermaid'

// https://vitepress.dev/reference/site-config
export default withMermaid(defineConfig({
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
        ],
        [
            'script',
            {async: '', src: 'https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-5210914487984731', crossorigin: 'anonymous'},
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
            {text: 'B站视频课程', link: 'https://space.bilibili.com/434377496/channel/collectiondetail?sid=4035213&ctype=0'},
            {text: '联系作者', link: 'https://nanmicoder.github.io/MediaCrawler/%E4%BD%9C%E8%80%85%E4%BB%8B%E7%BB%8D.html'},
            {text: '支持作者', link: 'https://nanmicoder.github.io/MediaCrawler/%E7%9F%A5%E8%AF%86%E4%BB%98%E8%B4%B9%E4%BB%8B%E7%BB%8D.html'},
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
            },
            {
                text: 'Python爬虫进阶',
                collapsed: false,
                items: [
                    {text: '01_工程化爬虫开发规范', link: '/爬虫进价/01_工程化爬虫开发规范'},
                    {text: '02_反爬虫对抗基础_请求伪装', link: '/爬虫进价/02_反爬虫对抗基础_请求伪装'},
                    {text: '03_代理IP的使用与管理', link: '/爬虫进价/03_代理IP的使用与管理'},
                    {text: '04_Playwright浏览器自动化入门', link: '/爬虫进价/04_Playwright浏览器自动化入门'},
                    {text: '05_Playwright进阶_反检测与性能优化', link: '/爬虫进价/05_Playwright进阶_反检测与性能优化'},
                    {text: '06_登录认证_Cookie与Session管理', link: '/爬虫进价/06_登录认证_Cookie与Session管理'},
                    {text: '07_登录认证_扫码与短信登录实现', link: '/爬虫进价/07_登录认证_扫码与短信登录实现'},
                    {text: '08_验证码识别与处理', link: '/爬虫进价/08_验证码识别与处理'},
                    {text: '09_数据清洗与预处理', link: '/爬虫进价/09_数据清洗与预处理'},
                    {text: '10_数据分析与可视化', link: '/爬虫进价/10_数据分析与可视化'},
                    {text: '11_进阶综合实战项目', link: '/爬虫进价/11_进阶综合实战项目'}
                ]
            }
        ],

        socialLinks: [
            {icon: 'github', link: 'https://github.com/NanmiCoder/CrawlerTutorial'}
        ]
    },

}))
