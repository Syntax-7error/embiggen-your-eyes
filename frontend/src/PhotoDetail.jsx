import React, {useState,useEffect} from 'react';
import {useParams,Link} from 'react-router-dom';
 

function PhotoDetail() {

  const {id} = useParams();
  const [photo,setPhoto] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchPhoto() {


      try{
        const YOUR_API_KEY = "Vi3TWaHpEpk74KfBEsEbYP4hM-mi6kFhQBV6D2bPA6A";
        const API_URL = `https://api.unsplash.com/photos/${id}?client_id=${YOUR_API_KEY}`;

        const response = await fetch(API_URL);

        if(!response.ok){
          throw new Error('Photo not found');

        }
        const data = await response.json();
        setPhoto(data);

      }catch(error){
        console.error("error fetching photo details ", error);
        
      }finally {
        setLoading(false);
      }
      
    }
    fetchPhoto();
  },[id]);

  if(loading){
    return <div>loading</div>;
  }

  if(!photo){
    return <div>Photo not found</div>;
  }
  
  return (
    <div className="photo-detail-container">

    <Link to="/" className="back-link">back to search</Link>
    <img src={photo.urls.regular} alt={photo.alt_description} className="photo-detail-image" />
    <div className="photo-info">
        <p>{photo.description || 'No description available.'}</p>
        <p>By: {photo.user.name}</p>
        <a href={photo.links.html} target="_blank" rel="noopener noreferrer">View on Unsplash</a>
      </div>
    </div>

  );
}

export default PhotoDetail;
