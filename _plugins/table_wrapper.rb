module Jekyll
  module TableWrapperFilter
    # Wrap content <table> tags in a scrollable div for mobile
    # Skips rouge-table (code block tables)
    def wrap_tables(input)
      # Use a simple state machine: find each <table...>...</table> block
      # and wrap non-rouge ones
      output = input.dup
      output.gsub!(%r{<table\b([^>]*)>(.*?)</table>}m) do
        attrs = $1
        inner = $2
        if attrs.include?('rouge-table')
          # Keep rouge tables unwrapped
          "<table#{attrs}>#{inner}</table>"
        else
          "<div class=\"table-wrapper\"><table#{attrs}>#{inner}</table></div>"
        end
      end
      output
    end
  end
end

Liquid::Template.register_filter(Jekyll::TableWrapperFilter)
