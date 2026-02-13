/**
 * GA4 Custom Event Tracking for AIコンパス
 * Tracks: CTA clicks, scroll depth, time on page, affiliate clicks, social shares
 */
(function() {
  'use strict';

  function safeGtag() {
    if (typeof window.gtag === 'function') {
      window.gtag.apply(null, arguments);
    }
  }

  // 1. CTA & Link Click Tracking
  document.addEventListener('click', function(e) {
    var link = e.target.closest('a');
    if (!link) return;

    var href = link.getAttribute('href') || '';

    // Consulting CTA clicks
    if (link.closest('.consulting-cta') || link.closest('.consulting-cta-link') ||
        href.indexOf('/contact/') !== -1 || href.indexOf('allforces.wuaze.com') !== -1) {
      var ctaLocation = 'other';
      if (link.closest('.consulting-cta--sidebar')) ctaLocation = 'sidebar';
      else if (link.closest('.consulting-cta--post')) ctaLocation = 'post_footer';
      else if (link.closest('.consulting-cta--home')) ctaLocation = 'home';
      else if (link.closest('[class*="consulting"]')) ctaLocation = 'inline';

      safeGtag('event', 'cta_click', {
        event_category: 'consulting',
        event_label: href,
        cta_location: ctaLocation,
        page_path: window.location.pathname
      });
    }

    // Service page clicks
    if (href.indexOf('/services/') !== -1) {
      safeGtag('event', 'service_page_click', {
        event_category: 'navigation',
        event_label: href,
        source_page: window.location.pathname
      });
    }

    // Amazon Associates clicks
    if (href.indexOf('amazon.co.jp') !== -1 && href.indexOf('tag=') !== -1) {
      safeGtag('event', 'affiliate_click', {
        event_category: 'amazon_associates',
        event_label: link.textContent.trim().substring(0, 100),
        source_article: window.location.pathname
      });
    }

    // Internal article link clicks (related posts)
    if (link.closest('.related-posts') || link.closest('.internal-links')) {
      safeGtag('event', 'internal_link_click', {
        event_category: 'engagement',
        event_label: href,
        link_type: link.closest('.related-posts') ? 'related_posts' : 'inline'
      });
    }

    // Social share clicks
    if (link.closest('.share-buttons') || link.closest('.share-button')) {
      var platform = 'other';
      if (href.indexOf('twitter.com') !== -1 || href.indexOf('x.com') !== -1) platform = 'twitter';
      else if (href.indexOf('facebook.com') !== -1) platform = 'facebook';
      else if (href.indexOf('linkedin.com') !== -1) platform = 'linkedin';
      else if (href.indexOf('hatena') !== -1) platform = 'hatena';

      safeGtag('event', 'social_share', {
        event_category: 'social',
        event_label: platform,
        source_article: window.location.pathname
      });
    }
  });

  // 2. Scroll Depth Tracking
  var scrollMilestones = [25, 50, 75, 90, 100];
  var scrollReached = {};

  function trackScrollDepth() {
    var docHeight = document.documentElement.scrollHeight - window.innerHeight;
    if (docHeight <= 0) return;
    var scrollPercent = Math.round((window.scrollY / docHeight) * 100);

    for (var i = 0; i < scrollMilestones.length; i++) {
      var milestone = scrollMilestones[i];
      if (scrollPercent >= milestone && !scrollReached[milestone]) {
        scrollReached[milestone] = true;
        safeGtag('event', 'scroll_depth', {
          event_category: 'engagement',
          event_label: milestone + '%',
          percent_scrolled: milestone,
          page_path: window.location.pathname
        });
      }
    }
  }

  var scrollTimer;
  window.addEventListener('scroll', function() {
    clearTimeout(scrollTimer);
    scrollTimer = setTimeout(trackScrollDepth, 200);
  }, { passive: true });

  // 3. Time on Page Tracking
  var isPageActive = true;
  document.addEventListener('visibilitychange', function() {
    isPageActive = !document.hidden;
  });

  var timeThresholds = [30, 60, 180, 300];
  for (var t = 0; t < timeThresholds.length; t++) {
    (function(seconds) {
      setTimeout(function() {
        if (isPageActive) {
          safeGtag('event', 'time_on_page', {
            event_category: 'engagement',
            event_label: seconds + 's',
            time_seconds: seconds,
            page_path: window.location.pathname
          });
        }
      }, seconds * 1000);
    })(timeThresholds[t]);
  }

  // 4. Article View with Category (content grouping)
  var categoryBadge = document.querySelector('.category-badge, .post-category, [class*="category-badge"]');
  if (categoryBadge) {
    var categoryName = categoryBadge.textContent.trim();
    safeGtag('set', { content_group: categoryName });
  }

  // Track article-specific metrics
  var postContent = document.querySelector('.post-content, .article-content');
  if (postContent) {
    var charCount = postContent.textContent.trim().length;
    safeGtag('event', 'article_view', {
      event_category: 'content',
      article_category: categoryBadge ? categoryBadge.textContent.trim() : 'uncategorized',
      char_count: charCount,
      page_path: window.location.pathname
    });
  }
})();
