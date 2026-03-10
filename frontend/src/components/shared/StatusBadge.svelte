<script>
  export let status = '';
  export let map = null;

  const DEFAULT_MAP = {
    active:      { label: 'Active',      color: 'green'  },
    approved:    { label: 'Approved',    color: 'green'  },
    completed:   { label: 'Completed',   color: 'green'  },
    answered:    { label: 'Answered',    color: 'green'  },
    pending:     { label: 'Pending',     color: 'yellow' },
    processing:  { label: 'Processing',  color: 'yellow' },
    in_progress: { label: 'In Progress', color: 'yellow' },
    inactive:    { label: 'Inactive',    color: 'red'    },
    failed:      { label: 'Failed',      color: 'red'    },
    cancelled:   { label: 'Cancelled',   color: 'red'    },
    rejected:    { label: 'Rejected',    color: 'red'    },
    draft:       { label: 'Draft',       color: 'gray'   },
    queued:      { label: 'Queued',      color: 'gray'   },
  };

  const COLOR_CLASSES = {
    green:  'bg-green-100 text-green-800',
    yellow: 'bg-yellow-100 text-yellow-800',
    red:    'bg-red-100 text-red-800',
    gray:   'bg-gray-100 text-gray-600',
    blue:   'bg-blue-100 text-blue-800',
  };

  $: effectiveMap = map ? { ...DEFAULT_MAP, ...map } : DEFAULT_MAP;

  $: entry = effectiveMap[status] || null;

  $: label = entry?.label ?? status;

  $: colorClass = COLOR_CLASSES[entry?.color] ?? COLOR_CLASSES.blue;
</script>

<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium {colorClass}">
  {label}
</span>
