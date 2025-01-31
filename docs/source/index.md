(target-spikewrap)=

<!-- We need the original #spikewrap header to give the page a title, but it is hard to center. 
So disappear it below then make centered title with html.
Was using a .{center} css like in datashuttle but this isn't working for some reason :S -->

```{raw} html
<style>
h1 { font-size: 0rem; }
</style>
```

# spikewrap

<p style="text-align: center; font-size: 48px; font-weight: bold;"> spikewrap </p>
<p style="text-align: center; font-size: 22px;">A Python package for managing extracellular electrophysiology pipelines.</p>
<p style="text-align: center; font-size: 22px;"><a href="gallery_builds/get_started/package_overview.html">1-minute overview</a></p>

::::{grid} 1 4 4 4 
:gutter: 4

:::{grid-item-card} {fas}`rocket;sd-text-primary` Get Started
:link: get_started/index
:link-type: doc

Setup ``spikewrap`` for your data.
:::

:::{grid-item-card} {fas}`book-open;sd-text-primary` Tutorials
:link: gallery_builds/tutorials/index
:link-type: doc

Long-form guides.
:::

:::{grid-item-card} {fas}`book-open;sd-text-primary` How To
:link: gallery_builds/how_to/index
:link-type: doc

Quick reference pages.

:::

:::{grid-item-card} {fas}`code;sd-text-primary` API Reference
:link: api_index
:link-type: doc

Full Python reference.

:::

::::

```{toctree}
:maxdepth: 2
:hidden:

get_started/index
gallery_builds/tutorials/index
gallery_builds/how_to/index
community/index
api_index
```
