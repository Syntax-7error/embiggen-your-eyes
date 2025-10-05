
import { Link } from 'react-router-dom';
import React,{ useState, useEffect } from 'react'

function Home() {
  const [searchTerm, setSearchTerm] = useState('');
  const [searchMode, setSearchMode] = useState('name');
  const [images, setImages] = useState([]);
  useEffect(()=>{
    const timerId = setTimeout(async () => {
      if(searchTerm){
        try{
        const YOUR_API_KEY = "Vi3TWaHpEpk74KfBEsEbYP4hM-mi6kFhQBV6D2bPA6A";
        const API_URL = `https://api.unsplash.com/search/photos?client_id=${YOUR_API_KEY}&query=${searchTerm}`;
          const response = await fetch(API_URL);

          if(!response.ok){
            throw new Error(`Http error status : "${response.status}`);
          }

          const data = await response.json();
          setImages(data.results);
          console.log("fetched and set images",data.results);
        }
        catch(error){
          console.error("Error fetching data:", error);
        }
      }else{
        setImages([]);
      }
    }, 500);

    return ()=>{
      clearTimeout(timerId);
    };
  },[searchTerm,searchMode]);
  
  return (
   <> 
    <video className="background-video" autoPlay loop muted >

    <source src="/background.mp4" type="video/mp4" />
    </video>
    <div className="search-modes">

<div className="search-container">

    <input className="search-bar" 
     type = "text"
     placeholder = "Enter the place you want to visit"
     value={searchTerm}
     onChange={(event)=>setSearchTerm(event.target.value)}
    />


      <button className={searchMode === 'name'?'active':''} onClick={()=> setSearchMode('name')}>By Name</button>
      <button className={searchMode === 'coordinate' ? 'active':''} onClick={()=> setSearchMode('coordinate')}>By Coordinate</button>
      <button className={searchMode === 'ai'? 'active':''} onClick={()=> setSearchMode('ai')}>AI Mode</button>
    </div>
    </div>
    <div className="image-grid">

      {images.map(image=>(
          <Link key={image.id} to={`/photo/${image.id}`}>
            <img src={image.urls.small} alt={image.alt_description} />
          </Link>
      ))}
    </div>
    </>
  );
}

export default Home;
