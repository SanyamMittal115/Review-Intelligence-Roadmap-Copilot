export default async function handler(req,res){
  try{
    const id=String(req.query?.id||'').trim();
    const requested=Math.min(500,Math.max(1,parseInt(req.query?.count||'150',10)||150));
    if(!id)return res.status(400).json({error:'App id required'});

    const reviews=[];
    const seen=new Set();
    const maxPages=10;

    for(let p=1;p<=maxPages && reviews.length<requested;p++){
      const u=`https://itunes.apple.com/us/rss/customerreviews/page=${p}/id=${encodeURIComponent(id)}/sortby=mostrecent/json`;
      const r=await fetch(u,{headers:{Accept:'application/json','User-Agent':'Mozilla/5.0'}});
      if(!r.ok)continue;
      const d=await r.json();
      const entries=Array.isArray(d?.feed?.entry)?d.feed.entry:[];
      for(const e of entries){
        if(reviews.length>=requested)break;
        if(!e?.['im:rating'])continue;
        const review=e?.content?.label||'';
        const rating=Number(e['im:rating']?.label||0);
        const title=e?.title?.label||'';
        const author=e?.author?.name?.label||'';
        const version=e?.['im:version']?.label||'';
        const key=e?.id?.label||`${author}|${title}|${review}|${rating}`;
        if(!review||seen.has(key))continue;
        seen.add(key);
        reviews.push({review,rating,title,author,version});
      }
    }

    res.setHeader('Cache-Control','no-store, max-age=0');
    res.status(200).json({
      reviews:reviews.slice(0,requested),
      requested,
      returned:Math.min(reviews.length,requested),
      complete:reviews.length>=requested,
      message:reviews.length>=requested?`Loaded exactly ${requested} unique reviews.`:`Only ${reviews.length} unique reviews were available from Apple's public feed; ${requested} were requested.`
    });
  }catch(e){res.status(500).json({error:e.message})}
}