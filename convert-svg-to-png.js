const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

async function convertSvgToPng() {
    const browser = await puppeteer.launch();
    const page = await browser.newPage();
    
    // Read SVG content
    const svgContent = fs.readFileSync('./assets/images/og-image.svg', 'utf8');
    
    // Create HTML page with SVG
    const html = `
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { margin: 0; padding: 0; background: white; }
            svg { display: block; }
        </style>
    </head>
    <body>
        ${svgContent}
    </body>
    </html>`;
    
    // Set content and viewport
    await page.setContent(html);
    await page.setViewport({ width: 1200, height: 630 });
    
    // Take screenshot
    await page.screenshot({ 
        path: './assets/images/og-image.png',
        type: 'png',
        fullPage: false
    });
    
    console.log('OG image PNG created successfully');
    
    // Create smaller logo version (180x180 for favicon base)
    await page.setViewport({ width: 180, height: 180 });
    
    // Create focused logo HTML for smaller version
    const logoHtml = `
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { margin: 0; padding: 0; background: linear-gradient(135deg, #10b981, #059669); display: flex; align-items: center; justify-content: center; }
        </style>
    </head>
    <body>
        <svg width="140" height="140" viewBox="0 0 140 140" xmlns="http://www.w3.org/2000/svg">
            <!-- Background Circle -->
            <circle cx="70" cy="70" r="60" fill="rgba(255,255,255,0.15)" stroke="rgba(255,255,255,0.3)" stroke-width="2"/>
            
            <!-- AI Brain Symbol -->
            <path d="M70 30C90 30 105 45 105 65C105 75 100 85 95 90C100 95 105 105 105 115C105 135 90 150 70 150C50 150 35 135 35 115C35 105 40 95 45 90C40 85 35 75 35 65C35 45 50 30 70 30Z" 
                  fill="#ffffff" opacity="0.9"/>
            
            <!-- Neural Network Lines -->
            <g stroke="#10b981" stroke-width="2" opacity="0.8">
                <line x1="50" y1="70" x2="90" y2="70"/>
                <line x1="50" y1="90" x2="90" y2="90"/>
                <line x1="50" y1="110" x2="90" y2="110"/>
                <line x1="60" y1="60" x2="80" y2="80"/>
                <line x1="80" y1="60" x2="60" y2="80"/>
            </g>
            
            <!-- Neural Nodes -->
            <circle cx="50" cy="70" r="4" fill="#10b981"/>
            <circle cx="90" cy="70" r="4" fill="#10b981"/>
            <circle cx="50" cy="90" r="4" fill="#10b981"/>
            <circle cx="90" cy="90" r="4" fill="#10b981"/>
            <circle cx="50" cy="110" r="4" fill="#10b981"/>
            <circle cx="90" cy="110" r="4" fill="#10b981"/>
            <circle cx="70" cy="75" r="5" fill="#059669"/>
            <circle cx="70" cy="105" r="5" fill="#059669"/>
        </svg>
    </body>
    </html>`;
    
    await page.setContent(logoHtml);
    await page.screenshot({ 
        path: './assets/images/logo.png',
        type: 'png',
        fullPage: false
    });
    
    console.log('Logo PNG created successfully');
    
    // Create apple-touch-icon (180x180)
    await page.screenshot({ 
        path: './assets/images/apple-touch-icon.png',
        type: 'png',
        fullPage: false
    });
    
    console.log('Apple touch icon created successfully');
    
    await browser.close();
}

convertSvgToPng().catch(console.error);