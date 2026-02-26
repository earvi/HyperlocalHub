<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="3.0" 
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:atom="http://www.w3.org/2005/Atom" 
                xmlns:dc="http://purl.org/dc/elements/1.1/"
                exclude-result-prefixes="atom dc">
    
    <xsl:output method="html" version="1.0" encoding="UTF-8" indent="yes"/>

    <xsl:template match="/">
        <html xmlns="http://www.w3.org/1999/xhtml" lang="en">
            <head>
                <title>HyperlocalHub RSS Feed</title>
                <link rel="stylesheet" href="/static/css/style.css"/>
                <!-- Bootstrap Icons for flair -->
                <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css"/>
                <style>
                    body {
                        padding: 2rem;
                        max-width: 900px;
                        margin: 0 auto;
                    }
                    .rss-header {
                        text-align: center;
                        margin-bottom: 3rem;
                    }
                </style>
            </head>
            <body>
                <div class="rss-header">
                    <h1 class="page-title">
                        <i class="bi bi-rss-fill me-2"></i>
                        <xsl:value-of select="/rss/channel/title"/>
                    </h1>
                    <p class="text-muted"><xsl:value-of select="/rss/channel/description"/></p>
                    <div class="alert glass-card d-inline-block mt-3 px-4 py-2">
                        <i class="bi bi-info-circle me-2 text-primary"></i>
                        <small class="text-muted">RSS Feed: Copy URL to your reader</small>
                    </div>
                </div>

                <div class="d-flex flex-column gap-3">
                    <xsl:for-each select="/rss/channel/item">
                        <div class="glass-card p-4">
                            <div class="d-flex justify-content-between align-items-start mb-2">
                                <h3 class="h5 m-0" style="font-weight: 700;">
                                    <a href="{link}" target="_blank" rel="noopener noreferrer" class="text-decoration-none alert-title">
                                        <xsl:value-of select="title"/>
                                    </a>
                                </h3>
                                <xsl:if test="category">
                                    <span class="category-badge border-glass text-muted small">
                                        <xsl:value-of select="category"/>
                                    </span>
                                </xsl:if>
                            </div>
                            
                            <p class="text-muted mb-3">
                                <xsl:value-of select="description" disable-output-escaping="yes"/>
                            </p>
                            
                            <div class="d-flex justify-content-between align-items-center">
                                <small class="text-muted">
                                    <i class="bi bi-calendar-event me-1"></i>
                                    <xsl:value-of select="pubDate"/>
                                </small>
                                <a href="{link}" target="_blank" class="btn btn-primary btn-sm py-1 px-3" style="font-size: 0.8rem;">
                                    Read Article <i class="bi bi-arrow-right ms-1"></i>
                                </a>
                            </div>
                        </div>
                    </xsl:for-each>
                </div>
            </body>
        </html>
    </xsl:template>
</xsl:stylesheet>